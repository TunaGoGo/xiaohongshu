# Xiaohongshu Note Generator

## Warnings
1. Pls place own AI APIs in .env file

## Function
1. Split the markdown file into chapters
2. Convert the chapter content into Xiaohongshu notes

## Usage
1. Put the markdown file in the books directory
2. Run break_down.py to split the markdown file into chapters
3. Run xiaohongshu.py to convert the chapter content into Xiaohongshu notes

## Notes
1. Please ensure that the network is unobstructed, otherwise the API request may fail
2. Please ensure that the format of the input markdown file is correct, otherwise the segmentation may fail
3. Please ensure that the content of the input markdown file is complete, otherwise the note generation may fail
4. Please ensure that the content of the input markdown file meets the format requirements of Xiaohongshu notes, otherwise the note generation may fail