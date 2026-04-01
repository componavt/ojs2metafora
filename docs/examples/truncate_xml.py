#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сокращения текста в элементах <text> и <abstract> XML-файла.
Оставляет только первые N слов в текстовых элементах.
Обрабатывает оба языка: RUS и ENG.
НЕ трогает другие элементы с атрибутом lang (secTitle, artTitle, и др.)
"""

import xml.etree.ElementTree as ET
import argparse
import sys
from pathlib import Path


def read_xml_with_encoding(input_file):
    """
    Читает XML-файл с автоматическим определением кодировки.
    """
    encodings_to_try = ['utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'windows-1251', 'cp1251', 'utf-8']
    
    for encoding in encodings_to_try:
        try:
            with open(input_file, 'r', encoding=encoding) as f:
                content = f.read()
            return content, encoding
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Если ничего не подошло, читаем как бинарный и пробуем декодировать
    with open(input_file, 'rb') as f:
        raw = f.read()
    
    # Пробуем определить по BOM
    if raw.startswith(b'\xff\xfe'):
        content = raw.decode('utf-16-le')
        return content, 'utf-16-le'
    elif raw.startswith(b'\xfe\xff'):
        content = raw.decode('utf-16-be')
        return content, 'utf-16-be'
    
    raise UnicodeDecodeError('utf-8', b'', 0, 1, 'Не удалось определить кодировку файла')


def truncate_text(text_content, max_words=3, add_ellipsis=True):
    """
    Сокращает текст до первых N слов.
    
    Args:
        text_content: Исходный текст
        max_words: Количество слов для сохранения
        add_ellipsis: Добавлять " ..." в конце
    
    Returns:
        Сокращённый текст
    """
    if not text_content:
        return text_content
    
    words = text_content.split()
    
    # Если слов меньше или равно max_words, не сокращаем
    if len(words) <= max_words:
        return text_content
    
    truncated = ' '.join(words[:max_words])
    
    if add_ellipsis:
        truncated += ' ...'
    
    return truncated


def truncate_text_in_xml(input_file, output_file, max_words=3, 
                          elements_to_process=None, add_ellipsis=True):
    """
    Сокращает текст в указанных элементах XML.
    
    Args:
        input_file: Путь к входному XML-файлу
        output_file: Путь к выходному XML-файлу
        max_words: Количество слов для сохранения
        elements_to_process: Список имён элементов для обработки
        add_ellipsis: Добавлять " ..." после сокращения
    
    Returns:
        tuple: (количество обработанных элементов, кодировка входа)
    """
    # Проверяем существование входного файла
    if not Path(input_file).exists():
        print(f"❌ Ошибка: Файл '{input_file}' не найден", file=sys.stderr)
        sys.exit(1)
    
    # Читаем файл с определением кодировки
    content, detected_encoding = read_xml_with_encoding(input_file)
    
    # Парсим XML
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"❌ Ошибка парсинга XML: {e}", file=sys.stderr)
        sys.exit(1)
    
    # По умолчанию обрабатываем ТОЛЬКО <text> и <abstract>
    if elements_to_process is None:
        elements_to_process = ['text', 'abstract']
    
    # Счётчик обработанных элементов
    processed_count = 0
    
    # Находим все указанные элементы (независимо от атрибута lang)
    for elem_name in elements_to_process:
        for elem in root.iter(elem_name):
            text_content = elem.text
            
            if text_content:
                # Сокращаем текст
                truncated = truncate_text(text_content, max_words, add_ellipsis)
                
                # Обновляем только если текст изменился
                if truncated != text_content:
                    elem.text = truncated
                    processed_count += 1
    
    # Сохраняем результат в UTF-8 с BOM для совместимости
    try:
        xml_str = ET.tostring(root, encoding='unicode')
        
        with open(output_file, 'w', encoding='utf-8-sig') as f:
            f.write(xml_str)
        
        return processed_count, detected_encoding
    
    except Exception as e:
        print(f"❌ Ошибка записи файла: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    # Настройка парсера аргументов
    parser = argparse.ArgumentParser(
        description='Сокращение текста в элементах <text> и <abstract> XML-файла',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  %(prog)s petrsu_long.xml petrsu_short.xml
  %(prog)s input.xml output.xml --words 5
  %(prog)s input.xml output.xml --words 3 --elements text abstract
  %(prog)s input.xml output.xml --no-ellipsis
        '''
    )
    
    parser.add_argument(
        'input_file',
        help='Путь к входному XML-файлу'
    )
    
    parser.add_argument(
        'output_file',
        help='Путь к выходному XML-файлу'
    )
    
    parser.add_argument(
        '-w', '--words',
        type=int,
        default=3,
        metavar='N',
        help='Количество слов для сохранения (по умолчанию: 3)'
    )
    
    parser.add_argument(
        '-e', '--elements',
        type=str,
        nargs='+',
        metavar='ELEM',
        help='Список элементов для обработки (по умолчанию: text abstract)'
    )
    
    parser.add_argument(
        '--no-ellipsis',
        action='store_true',
        help='Не добавлять " ..." после сокращённого текста'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Вывод подробной информации'
    )
    
    # Парсинг аргументов
    args = parser.parse_args()
    
    # Вывод информации о параметрах
    if args.verbose:
        print(f"📁 Входной файл:  {args.input_file}")
        print(f"📁 Выходной файл: {args.output_file}")
        print(f"📝 Слов:         {args.words}")
        print(f"🏷️ Элементы:     {args.elements if args.elements else 'text, abstract'}")
        print(f"🔤 Многоточие:   {'нет' if args.no_ellipsis else 'да'}")
        print("-" * 50)
    
    # Обработка файла
    processed, encoding = truncate_text_in_xml(
        args.input_file,
        args.output_file,
        max_words=args.words,
        elements_to_process=args.elements,
        add_ellipsis=not args.no_ellipsis
    )
    
    # Вывод результата
    if args.verbose:
        print(f"🔤 Кодировка:     {encoding}")
        print(f"✅ Обработано элементов: {processed}")
    
    print(f"✓ Файл успешно обработан: {args.output_file}")
    print(f"  Кодировка входа: {encoding}")
    print(f"  Сокращено элементов: {processed}")


if __name__ == '__main__':
    main()
