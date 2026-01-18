import pytesseract
from pytesseract import Output


def has_text_confidence(img_path):
    data = pytesseract.image_to_data(img_path, output_type=Output.DICT)
    word_confidences = [int(conf) for conf in data['conf'] if conf != '-1']
    if len(word_confidences) == 0:
        return False
    avg_confidence = sum(word_confidences) / len(word_confidences)
    return avg_confidence > 30


def read_image(img_path, lang='eng'):
    try:
        if not has_text_confidence(img_path):
            return "[NO TEXT DETECTED - LOW CONFIDENCE]"
        
        custom_config = r'--psm 3'
        text = pytesseract.image_to_string(img_path, lang=lang, config=custom_config)
        if not text.strip():
            return "[NO TEXT DETECTED]"
        return text.strip()
    except Exception as e:
        return f"[OCR ERROR] {str(e)}"
