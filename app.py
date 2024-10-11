from flask import Flask, render_template, request, send_file
from PIL import Image, ImageEnhance
import os
import piexif
import random
from datetime import datetime
import psycopg2  # For PostgreSQL database connection

app = Flask(__name__)

# Folder to store images
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Convert decimal degrees to degrees, minutes, seconds for EXIF
def decimal_to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(((deg - d) * 60 - m) * 60)
    return (d, m, s)

# Randomize camera make and model if not provided
def randomize_camera_data(camera_make=None, camera_model=None):
    makes = ["Canon", "Nikon", "Sony", "Apple", "Samsung", "GoPro", "Huawei"]
    models = {
        "Canon": ["EOS 5D Mark IV", "Rebel T6", "EOS R"],
        "Nikon": ["D850", "Z7", "D7500"],
        "Sony": ["Alpha a7 III", "Alpha a6400"],
        "Apple": ["iPhone 12 Pro", "iPhone X", "iPhone 13"],
        "Samsung": ["Galaxy S21", "Galaxy Note 10"],
        "GoPro": ["HERO9 Black", "HERO8 Black"],
        "Huawei": ["P40 Pro", "Mate 30 Pro"]
    }

    if not camera_make:
        camera_make = random.choice(makes)
    if not camera_model:
        camera_model = random.choice(models[camera_make])
    
    return camera_make, camera_model

# Function to apply random transformations to the image
def apply_random_transformations(img):
    img = img.rotate(random.uniform(-10, 10))  # Random rotation
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(random.uniform(0.8, 1.2))  # Random contrast adjustment
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(random.uniform(0.8, 1.2))  # Random brightness adjustment
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(random.uniform(0.9, 1.1))  # Random color enhancement
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(random.uniform(0.9, 1.1))  # Random sharpness adjustment
    return img

# Function to add custom or randomized EXIF metadata to the image
def add_custom_exif_metadata(image_path, output_path, camera_make, camera_model, date_taken, latitude, longitude):
    img = Image.open(image_path)
    img = apply_random_transformations(img)
    camera_make, camera_model = randomize_camera_data(camera_make, camera_model)

    lat_dms = decimal_to_dms(float(latitude)) if latitude else decimal_to_dms(random.uniform(-90, 90))
    lon_dms = decimal_to_dms(float(longitude)) if longitude else decimal_to_dms(random.uniform(-180, 180))

    if not date_taken:
        date_taken = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
    else:
        date_taken = datetime.strptime(date_taken, "%Y-%m-%dT%H:%M").strftime("%Y:%m:%d %H:%M:%S")

    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: camera_make.encode('utf-8'),
            piexif.ImageIFD.Model: camera_model.encode('utf-8'),
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: date_taken.encode('utf-8'),
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: 'N' if float(latitude) >= 0 else 'S',
            piexif.GPSIFD.GPSLatitude: ((lat_dms[0], 1), (lat_dms[1], 1), (lat_dms[2], 1)),
            piexif.GPSIFD.GPSLongitudeRef: 'E' if float(longitude) >= 0 else 'W',
            piexif.GPSIFD.GPSLongitude: ((lon_dms[0], 1), (lon_dms[1], 1), (lon_dms[2], 1)),
        }
    }

    exif_bytes = piexif.dump(exif_dict)
    img.save(output_path, "jpeg", exif=exif_bytes)

# Function to connect to the PostgreSQL database
def connect_to_database():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

# Route to the homepage
@app.route('/')
def home():
    return render_template('index.html')  # Ensure this template exists in the templates directory

# Test route
@app.route('/test')
def test():
    return "This is a test route!"  # Simple text response for testing

# Route to handle image upload, transformation, and EXIF customization
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return "No image file uploaded", 400  # Return a 400 error

    file = request.files['image']
    if file.filename == '':
        return "No image selected", 400  # Return a 400 error

    camera_make = request.form.get('camera_make')
    camera_model = request.form.get('camera_model')
    date_taken = request.form.get('date_taken')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"modified_{file.filename}")
    add_custom_exif_metadata(filepath, output_path, camera_make, camera_model, date_taken, latitude, longitude)

    # Optional: Connect to the database to perform any operations
    conn = connect_to_database()
    if conn:
        # Perform database operations if needed
        conn.close()  # Close the connection

    return send_file(output_path, mimetype='image/jpeg', download_name=f"modified_{file.filename}", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))


