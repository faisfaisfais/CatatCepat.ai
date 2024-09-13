const recordBtn = document.querySelector(".record"),
  editor = CKEDITOR.instances.editor,
  downloadBtn = document.querySelector(".download"),
  inputLanguage = document.querySelector("#language"),
  clearBtn = document.querySelector(".clear"),
  uploadBtn = document.querySelector("#uploadBtn"),
  fileInput = document.querySelector("#fileInput");

const dropArea = document.querySelector('.drop-section')
const listSection = document.querySelector('.list-section')
const listContainer = document.querySelector('.list')
const fileSelector = document.querySelector('.file-selector')
const fileSelectorInput = document.querySelector('.file-selector-input')

let SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition,
  recognition,
  recording = false;

function populateLanguages() {
  languages.forEach((lang) => {
    const option = document.createElement("option");
    option.value = lang.code;
    option.innerHTML = lang.name;
    inputLanguage.appendChild(option);
  });
}

populateLanguages();

function speechToText() {
  try {
    recognition = new SpeechRecognition();
    recognition.lang = inputLanguage.value;
    recognition.interimResults = true;
    recordBtn.classList.add("recording");
    recordBtn.querySelector("p").innerHTML = "Listening...";
    recognition.start();
    recognition.onresult = (event) => {
        const speechResult = event.results[0][0].transcript;
        if (event.results[0].isFinal) {
            editor.insertHtml(" " + speechResult);
            saveTranscription(speechResult); // Save the final transcription
        } else {
            const interimText = document.querySelector(".interim");
            if (interimText) {
                interimText.innerHTML = " " + speechResult;
            } else {
                editor.insertHtml("<p class='interim'>" + speechResult + "</p>");
            }
        }
        downloadBtn.disabled = false;
    };
    recognition.onspeechend = () => {
      speechToText();
    };
    recognition.onerror = (event) => {
      stopRecording();
      if (event.error === "no-speech") {
        alert("No speech was detected. Stopping...");
      } else if (event.error === "audio-capture") {
        alert("No microphone was found. Ensure that a microphone is installed.");
      } else if (event.error === "not-allowed") {
        alert("Permission to use microphone is blocked.");
      } else if (event.error === "aborted") {
        alert("Listening Stopped.");
      } else {
        alert("Error occurred in recognition: " + event.error);
      }
    };
  } catch (error) {
    recording = false;
    console.log(error);
  }
}

recordBtn.addEventListener("click", () => {
  if (!recording) {
    speechToText();
    recording = true;
  } else {
    stopRecording();
  }
});

function stopRecording() {
  recognition.stop();
  recordBtn.querySelector("p").innerHTML = "Start Listening";
  recordBtn.classList.remove("recording");
  recording = false;
}

function uploadAndTranscribe() {
  const file = fileInput.files[0];
  if (!file) {
    alert("Please select a file first!");
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  fetch('/transcribe', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      alert(data.error);
    } else {
      editor.setData(data.text);
    }
  })
  .catch(error => {
    console.error('Error:', error);
    alert('An error occurred during transcription.');
  });
}

uploadBtn.addEventListener("click", uploadAndTranscribe);     

// document.getElementById('fileInput').addEventListener('change', function(event) {
//   const filePreview = document.getElementById('filePreview');
//   const file = event.target.files[0];

//   // Clear the preview area
//   filePreview.innerHTML = '';

//   if (file) {
//       // Display the file name
//       const fileName = document.createElement('p');
//       fileName.textContent = `Selected file: ${file.name}`;
//       filePreview.appendChild(fileName);

//       // Create a preview depending on the file type
//       if (file.type.startsWith('audio/')) {
//           const audioPreview = document.createElement('audio');
//           audioPreview.controls = true;
//           audioPreview.src = URL.createObjectURL(file);
//           filePreview.appendChild(audioPreview);
//       } else if (file.type.startsWith('video/')) {
//           const videoPreview = document.createElement('video');
//           videoPreview.controls = true;
//           videoPreview.src = URL.createObjectURL(file);
//           filePreview.appendChild(videoPreview);
//       } else {
//           const fileMessage = document.createElement('p');
//           fileMessage.textContent = "File preview not available.";
//           filePreview.appendChild(fileMessage);
//       }
//   } else {
//       // If no file is selected, show the default message
//       filePreview.innerHTML = '<p>No file selected</p>';
//   }
// });



// function download() {
//   const text = editor.getData();

//   // Create a new jsPDF instance
//   const { jsPDF } = window.jspdf;
//   const doc = new jsPDF();

//   // Add text to the PDF
//   doc.text(text, 10, 10);

//   // Save the PDF with the filename "speech.pdf"
//   doc.save("speech.pdf");
// }


downloadBtn.addEventListener("click", download);

clearBtn.addEventListener("click", () => {
  editor.setData("");
  downloadBtn.disabled = true;
});
