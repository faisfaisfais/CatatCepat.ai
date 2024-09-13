from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
import speech_recognition as sr
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from bson import ObjectId
import logging
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import os
import pymongo
from flask import render_template, redirect, url_for
from flask_login import current_user, login_required

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Necessary for session management

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to 'login' for @login_required

# URI MongoDB dan konfigurasi database
app.config["MONGO_URI"] = "mongodb+srv://faiszuhair23:CatatCepat@catatcepat.nqpf05k.mongodb.net/CatatCepat"
mongo = PyMongo(app)

# Folder untuk menyimpan file yang diupload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'mp4', 'm4a'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set the path to the ffmpeg and ffprobe executables
AudioSegment.converter = "C:\\ffmpeg\\bin\\ffmpeg.exe"
AudioSegment.ffprobe = "C:\\ffmpeg\\bin\\ffprobe.exe"

# Set up logging
logging.basicConfig(level=logging.INFO)

# Fungsi untuk mengecek ekstensi file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Fungsi untuk mengonversi MP3/M4A ke WAV
def convert_to_wav(file_path, target_path):
    logging.info(f"Converting {file_path} to {target_path}")
    audio = AudioSegment.from_file(file_path)
    audio.export(target_path, format="wav")
    return target_path

# Fungsi untuk melakukan transkripsi
def transcribe_audio(file_path):
    logging.info(f"Transcribing audio from {file_path}")
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio_data, language="id-ID,en-US")
    except sr.UnknownValueError:
        text = "Audio unclear or not understood."
    except sr.RequestError as e:
        text = f"Could not request results from Google Speech Recognition service; {e}"
    return text

# Fungsi untuk mengekstrak audio dari video dan transkripsi
def transcribe_video(file_path):
    logging.info(f"Extracting audio from {file_path}")
    video = VideoFileClip(file_path)
    audio_path = "temp_audio.wav"
    
    try:
        video.audio.write_audiofile(audio_path, codec='pcm_s16le')
        text = transcribe_audio(audio_path)
    finally:
        video.close()  # Pastikan video file ditutup setelah digunakan
        if os.path.exists(audio_path):
            os.remove(audio_path)  # Hapus file audio sementara
            logging.info(f"Deleted temporary audio file {audio_path}")
        
    return text

# User model for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.role = user_data['role']
    
    def is_admin(self):
        return self.role == 'admin'

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.user.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'user')  # Default role is 'user'

        if mongo.db.user.find_one({"username": username}):
            flash('Username already exists')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        mongo.db.user.insert_one({
            "username": username,
            "password": hashed_password,
            "role": role
        })
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_data = mongo.db.user.find_one({"username": username})
        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            flash('Logged in successfully.')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('public_index'))

@app.route('/navbar')
@login_required
def navbar():
    # Check if the user is authenticated and the current_user object is populated
    if current_user.is_authenticated:
        user_name = current_user.username  # This should fetch the user's name from the collection
        if current_user.role == 'admin':
            dashboard_url = url_for('admin_dashboard')  # Route to admin dashboard
        else:
            dashboard_url = url_for('user_dashboard')  # Route to user dashboard
        return render_template('navbar.html', user_name=user_name, dashboard_url=dashboard_url)
    
    return redirect(url_for('login'))  # Redirect to login if not authenticated

# @app.route('/admin/dashboard')
# @login_required
# def admin_dashboard():
#     if not current_user.is_admin():
#         flash('Access denied: Admins only.')
#         return redirect(url_for('index'))
    
#     # Example: Fetch all transcriptions
#     transcriptions = mongo.db.audio_file.find()
#     return render_template('admin_dashboard.html', transcriptions=transcriptions)

@app.route('/admin/users', methods=['GET'])
@login_required
def manage_users():
    if not current_user.is_admin():
        flash('Access denied: Admins only.')
        return redirect(url_for('index'))

    # Mengambil data dari MongoDB
    users = list(mongo.db.user.find())
    print(users)  # Log data user di terminal
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin():
        flash('Access denied: Admins only.')
        return redirect(url_for('index'))

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    if mongo.db.user.find_one({"username": username}):
        flash('Username already exists')
        return redirect(url_for('admin_dashboard'))

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    mongo.db.user.insert_one({
        "username": username,
        "password": hashed_password,
        "role": role
    })
    flash('User added successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/edit/<user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin():
        flash('Access denied: Admins only.')
        return redirect(url_for('index'))

    username = request.form['username']
    role = request.form['role']

    update_data = {
        "username": username,
        "role": role
    }

    if request.form['password']:
        hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        update_data['password'] = hashed_password

    mongo.db.user.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    flash('User updated successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/delete/<user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin():
        flash('Access denied: Admins only.')
        return redirect(url_for('index'))

    mongo.db.user.delete_one({"_id": ObjectId(user_id)})
    flash('User deleted successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/update_transcription/<file_type>/<file_id>', methods=['POST'])
@login_required
def update_transcription(file_type, file_id):
    # Check if the user owns this file
    collection = mongo.db.audio_file if file_type == 'audio' else mongo.db.recording_file
    transcription = collection.find_one({"_id": ObjectId(file_id), "user_id": current_user.id})

    if not transcription:
        return jsonify({"error": "Transcription not found or you don't have permission to update this file"}), 404
    
    new_text = request.form['text']
    collection.update_one({"_id": ObjectId(file_id)}, {"$set": {"text": new_text}})
    
    flash('Transcription updated successfully')
    return redirect(url_for('user_dashboard'))

@app.route('/delete_transcription/<file_type>/<file_id>', methods=['POST'])
@login_required
def delete_transcription(file_type, file_id):
    # Check if the user owns this file
    collection = mongo.db.audio_file if file_type == 'audio' else mongo.db.recording_file
    transcription = collection.find_one({"_id": ObjectId(file_id), "user_id": current_user.id})

    if not transcription:
        return jsonify({"error": "Transcription not found or you don't have permission to delete this file"}), 404
    
    collection.delete_one({"_id": ObjectId(file_id)})
    
    flash('Transcription deleted successfully')
    return redirect(url_for('user_dashboard'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        # Check if the user is an admin or a regular user
        if current_user.role == 'admin':
            dashboard_url = url_for('admin_dashboard')
        else:
            dashboard_url = url_for('user_dashboard')

        # Pass user and dashboard_url to the template
        return render_template('index.html', user=current_user, dashboard_url=dashboard_url)
    
    # If the user is not authenticated, render the public index page
    return render_template('public_index.html')

@app.route('/public_index')
def public_index():
    return render_template('public_index.html')

@app.route('/record')
@login_required
def record():
    # Check if user is admin or regular user
    if current_user.role == 'admin':
        dashboard_url = url_for('admin_dashboard')
    else:
        dashboard_url = url_for('user_dashboard')

    # Pass user and dashboard_url to the template
    return render_template('record.html', user=current_user, dashboard_url=dashboard_url)

@app.route('/upload')
@login_required
def upload():
    # Check if user is admin or regular user
    if current_user.role == 'admin':
        dashboard_url = url_for('admin_dashboard')
    else:
        dashboard_url = url_for('user_dashboard')

    # Pass user and dashboard_url to the template
    return render_template('upload.html', user=current_user, dashboard_url=dashboard_url)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    # Ambil data pengguna dari MongoDB
    users = list(mongo.db.user.find())
    # Konversi _id ke string agar bisa digunakan di template
    users = [{**user, '_id': str(user['_id'])} for user in users]

    # Kirim data users ke template admin_dashboard.html
    return render_template('admin_dashboard.html', users=users, user=current_user)

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    # Fetch transcriptions related to the current user from both collections
    audio_files = list(mongo.db.audio_file.find({"user_id": current_user.id}))
    recording_files = list(mongo.db.recording_file.find({"user_id": current_user.id}))

    # Render the user dashboard and pass the retrieved data
    return render_template('user_dashboard.html', audio_files=audio_files, recording_files=recording_files, user=current_user)

@app.route('/transcribe', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logging.info(f"File saved to {file_path}")
        
        try:
            if filename.rsplit('.', 1)[1].lower() == 'mp4':
                # If the file is a video, extract audio and transcribe
                text = transcribe_video(file_path)
            else:
                # If the file is audio (MP3/M4A), convert to WAV and transcribe
                if filename.rsplit('.', 1)[1].lower() in {'mp3', 'm4a'}:
                    wav_path = file_path.rsplit('.', 1)[0] + '.wav'
                    convert_to_wav(file_path, wav_path)
                    file_path = wav_path
                
                # Perform transcription on WAV file
                text = transcribe_audio(file_path)
            
            # Save transcription data into MongoDB and include the user ID
            transcription_data = {
                "filename": filename,
                "text": text,
                "user_id": current_user.id,  # Add the logged-in user's ID
                "username": current_user.username  # Add the logged-in user's username
            }
            
            # Insert into the audio_file collection
            mongo.db.audio_file.insert_one(transcription_data)
            
            return jsonify({"text": text})
        
        except Exception as e:
            logging.error(f"Error during transcription: {e}")
            return jsonify({"error": str(e)})
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)  # Delete the file after processing
                logging.info(f"Deleted file {file_path}")
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)  # Delete the converted WAV file
                logging.info(f"Deleted converted WAV file {wav_path}")
    
    return jsonify({"error": "File type not allowed"})

@app.route('/save_transcription', methods=['POST'])
@login_required
def save_transcription():
    data = request.get_json()
    if not data or 'text' not in data or 'filename' not in data:
        return jsonify({"error": "Invalid data"}), 400
    
    # Extract the filename and text from the data
    filename = data['filename']
    text = data['text']
    
    # Save the transcription data into MongoDB, including user info
    transcription_data = {
        "filename": filename,
        "text": text,
        "user_id": current_user.id,  # Add the logged-in user's ID
        "username": current_user.username  # Add the logged-in user's username
    }
    
    # Insert into the recording_file collection
    mongo.db.recording_file.insert_one(transcription_data)
    
    return jsonify({"message": "Transcription saved successfully"}), 200

@login_manager.unauthorized_handler
def unauthorized_callback():
    flash('You must be logged in to access this page.')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, port=5001)
