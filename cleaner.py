"""Data cleaning module for LetsExtract Cleaner Bot."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import REQUIRED_COLUMNS, RUSSIAN_ZONES, SEARCH_ENGINE_DOMAINS

logger = logging.getLogger(__name__)


class DataCleaner:
    """Encapsulates business logic for cleaning LetsExtract exports."""

    def __init__(self) -> None:
        self.stats: dict[str, int | float] = {}

    def clean_file(self, input_path: Path | str, output_path: Path | str) -> None:
        """Clean the input Excel file and save the result to ``output_path``."""
        input_path = Path(input_path)
        output_path = Path(output_path)

        logger.info("Starting cleaning for file %s", input_path)

        try:
            df = pd.read_excel(input_path)
        except Exception as exc:  # pragma: no cover - logging for runtime issues
            logger.error("Failed to read Excel file: %s", exc)
            raise

        original_count = len(df)
        self.stats = {
            "original": original_count,
            "removed_non_russian": 0,
            "removed_search": 0,
            "removed_duplicates": 0,
            "removed_empty": 0,
            "final": 0,
            "removed_percentage": 0.0,
        }

        self._validate_columns(df)

        # Keep only required columns.
        df = df[REQUIRED_COLUMNS].copy()

        # Filter Russian domains.
        df, removed_non_russian = self._filter_russian_domains(df)
        self.stats["removed_non_russian"] = removed_non_russian

        # Remove search engine domains.
        df, removed_search = self._filter_search_engines(df)
        self.stats["removed_search"] = removed_search

        # Drop duplicates by domain.
        before_duplicates = len(df)
        df = df.drop_duplicates(subset="Домен", keep="first")
        self.stats["removed_duplicates"] = before_duplicates - len(df)

        # Drop empty values in key columns.
        df, removed_empty = self._drop_empty_values(df)
        self.stats["removed_empty"] = removed_empty

        final_count = len(df)
        self.stats["final"] = final_count
        removed_total = original_count - final_count
        self.stats["removed_percentage"] = (
            (removed_total / original_count * 100) if original_count else 0.0
        )

        try:
            df.to_excel(output_path, index=False)
        except Exception as exc:  # pragma: no cover - logging for runtime issues
            logger.error("Failed to save cleaned Excel file: %s", exc)
            raise

        logger.info("Finished cleaning. Cleaned file saved to %s", output_path)

    def get_stats_message(self) -> str:
        """Return formatted statistics about the last cleaning run."""
        if not self.stats:
            return "Статистика недоступна."

        return (
            "📊 Статистика обработки:\n"
            f"• Исходное количество записей: {self.stats['original']}\n"
            f"• Конечное количество записей: {self.stats['final']}\n"
            f"• Удалено не-РФ доменов: {self.stats['removed_non_russian']}\n"
            f"• Удалено поисковиков: {self.stats['removed_search']}\n"
            f"• Удалено дублей: {self.stats['removed_duplicates']}\n"
            f"• Удалено пустых записей: {self.stats['removed_empty']}\n"
            f"• Процент удалённых записей: {self.stats['removed_percentage']:.2f}%"
        )

    def _validate_columns(self, df: pd.DataFrame) -> None:
        missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
        if missing:
            message = "Отсутствуют обязательные колонки: " + ", ".join(missing)
            logger.error(message)
            raise ValueError(message)

    def _filter_russian_domains(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        mask = df["Домен"].astype(str).str.lower().str.strip()
        is_russian = mask.apply(self._is_russian_domain)
        filtered_df = df[is_russian].copy()
        removed = len(df) - len(filtered_df)
        return filtered_df, removed

    def _filter_search_engines(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        mask = df["Домен"].astype(str).str.lower()
        search_mask = mask.apply(self._is_search_engine_domain)
        filtered_df = df[~search_mask].copy()
        removed = int(search_mask.sum())
        return filtered_df, removed

    def _drop_empty_values(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        cleaned_df = df.copy()
        for column in ["Значение", "Домен"]:
            cleaned_df[column] = cleaned_df[column].astype(str).str.strip()
        non_empty_df = cleaned_df[(cleaned_df["Значение"] != "") & (cleaned_df["Домен"] != "")]
        removed = len(cleaned_df) - len(non_empty_df)
        return non_empty_df, removed

    @staticmethod
    def _is_russian_domain(domain: str) -> bool:
        domain = domain.strip().lower()
        return any(domain.endswith(zone) for zone in RUSSIAN_ZONES)

    @staticmethod
    def _is_search_engine_domain(domain: str) -> bool:
        domain = domain.strip().lower()
        return any(exclusion in domain for exclusion in SEARCH_ENGINE_DOMAINS)
