
import easyocr

print("Loading OCR model...")

reader = easyocr.Reader(
    ['en', 'hi'],
    gpu=False
)

image_path = input("Enter the full path of your notice image: ")

results = reader.readtext(image_path)

print("\n--- EXTRACTED NOTICE TEXT ---")

if results:
    for item in results:
        print(item[1])
else:
    print("No text detected. Try another image.")

print("\nOCR test completed!")
