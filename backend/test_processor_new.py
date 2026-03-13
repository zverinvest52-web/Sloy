#!/usr/bin/env python3
"""Тест для модуля processor.py"""

import cv2
import numpy as np
from processor import process_image


def main():
    print("Тестирование processor.py...")

    # Проверяем наличие тестового изображения
    test_image = "test_cad_input.png"

    try:
        # Обрабатываем изображение
        result = process_image(test_image, output_dir="processed")

        print("\nOK Обработка завершена успешно!")
        print(f"  - Выровненное изображение: {result['warped_original']}")
        print(f"  - Векторный превью: {result['vector_preview']}")
        print(f"  - Найдено фигур: {result['shapes_count']}")

        if result['shapes']:
            print("\nОбнаруженные фигуры:")
            for i, shape in enumerate(result['shapes'], 1):
                print(f"  {i}. {shape['type']} (площадь: {shape['area']:.0f})")

        return True

    except Exception as e:
        print(f"\nERR Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
