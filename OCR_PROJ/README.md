Developed an optical character recognition REST API using fastapi that takes multiple images as input and outputs the text scanned from it as output using pytesseract where all the functions like transferring images to server and making tesseract process the images have been made asynchronous as both functions are I/O bound, making the application parallel processing friendly for servers with multiple cores.

Additionally, the API ensures storage space is always cleared of temp files after an api request is completed to ensure that storage in the server never fills up.

Addressed a major race condition issue that can occur in this API: if two image files in the api request have the exact same name, it can result in the same temp file being accessed by two different images simultaneously. To address this a countermeasure was implemented using a redis increment counter whose value is appended to the temp file's name to ensure that every image file in the api request has a unique temp file for it even if two separate api requests running concurrently have the same file name.

Redis caching was also implemented to boost the performance in scenarios where users provide identical API requests multiple times.

Additional optimization features were integrated to tesseract such as committing an initial check of the image to verify whether it has any text or not before making tesseract process the image, this aided in reducing processing time in scenarios where many images were invalid.