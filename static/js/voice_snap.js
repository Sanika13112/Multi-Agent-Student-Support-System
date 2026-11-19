document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("voiceSnapUploadForm");
  const audioInput = document.getElementById("voiceSnapAudio");
  const uploadButton = document.getElementById("voiceSnapUploadButton");
  const status = document.getElementById("voiceSnapStatus");
  const audioInfo = document.getElementById("voiceSnapAudioInfo");
  const transcriptPanel = document.getElementById("voiceSnapTranscriptPanel");
  const transcriptEl = document.getElementById("voiceSnapTranscript");
  const languageEl = document.getElementById("voiceSnapLanguage");
  const notesPanel = document.getElementById("voiceSnapNotesPanel");
  const notesStatus = document.getElementById("voiceSnapNotesStatus");
  const notesEl = document.getElementById("voiceSnapNotes");
  const quickButton = document.getElementById("voiceSnapQuickButton");
  const detailedButton = document.getElementById("voiceSnapDetailedButton");
  const downloadActions = document.getElementById("voiceSnapDownloadActions");
  const downloadButton = document.getElementById("voiceSnapDownloadButton");
  const resetButton = document.getElementById("voiceSnapResetButton");

  let currentNotesMode = "detailed";

  function showStatus(element, message, kind = "info") {
    element.textContent = message || "";
    element.className = `status mt-3 ${kind}`;
  }

  function setBusy(busy) {
    uploadButton.disabled = busy;
    quickButton.disabled = busy;
    detailedButton.disabled = busy;
    uploadButton.textContent = busy ? "Processing..." : "Transcribe audio";
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = audioInput.files[0];
    if (!file) {
      showStatus(status, "Choose an audio file first.", "error");
      return;
    }
    if (file.size > 100 * 1024 * 1024) {
      showStatus(status, "The audio file exceeds the 100 MB limit.", "error");
      return;
    }

    const data = new FormData();
    data.append("audio", file);
    setBusy(true);
    showStatus(status, "Transcribing audio locally. Longer recordings may take a few minutes...", "info");
    audioInfo.textContent = "";
    notesPanel.hidden = true;
    transcriptPanel.hidden = true;
    downloadActions.hidden = true;
    notesEl.textContent = "";

    try {
      const response = await fetch("/api/voice-snap/upload", { method: "POST", body: data });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.message || "Transcription failed.");

      transcriptEl.textContent = result.transcript;
      languageEl.textContent = `Language: ${result.language || "Unknown"}`;
      audioInfo.textContent = `${result.filename} · ${result.duration || 0} seconds`;
      transcriptPanel.hidden = false;
      notesPanel.hidden = false;
      showStatus(status, "Transcription completed successfully.", "success");
    } catch (error) {
      showStatus(status, error.message || "Something went wrong during transcription.", "error");
    } finally {
      setBusy(false);
    }
  });

  async function generateNotes(mode) {
    setBusy(true);
    showStatus(notesStatus, `Generating ${mode} notes with the local AI model...`, "info");
    downloadActions.hidden = true;
    try {
      const response = await fetch("/api/voice-snap/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode })
      });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.message || "Notes generation failed.");

      currentNotesMode = mode;
      if (window.marked && typeof window.marked.parse === "function") {
        const html = window.marked.parse(result.notes);
        // Sanitise model output before inserting it as HTML.
        notesEl.innerHTML = window.DOMPurify ? window.DOMPurify.sanitize(html) : html;
      } else {
        notesEl.textContent = result.notes;
      }
      downloadButton.href = `/api/voice-snap/download?mode=${encodeURIComponent(mode)}`;
      downloadActions.hidden = false;
      showStatus(notesStatus, `${mode === "quick" ? "Quick" : "Detailed"} notes generated.`, "success");
    } catch (error) {
      showStatus(notesStatus, error.message || "Notes generation failed.", "error");
    } finally {
      setBusy(false);
    }
  }

  quickButton.addEventListener("click", () => generateNotes("quick"));
  detailedButton.addEventListener("click", () => generateNotes("detailed"));

  resetButton.addEventListener("click", async () => {
    try {
      await fetch("/api/voice-snap/reset", { method: "POST" });
      form.reset();
      transcriptPanel.hidden = true;
      notesPanel.hidden = true;
      downloadActions.hidden = true;
      transcriptEl.textContent = "";
      notesEl.textContent = "";
      audioInfo.textContent = "";
      showStatus(status, "VoiceSnap has been reset.", "success");
      showStatus(notesStatus, "");
    } catch {
      showStatus(status, "Could not reset VoiceSnap. Please refresh the page.", "error");
    }
  });

  // Restore transcript visibility after a page refresh within the same session.
  fetch("/api/voice-snap/transcript")
    .then((response) => response.json())
    .then((result) => {
      if (result.success && result.available) {
        transcriptEl.textContent = result.transcript;
        languageEl.textContent = `Language: ${result.language || "Unknown"}`;
        audioInfo.textContent = result.filename;
        transcriptPanel.hidden = false;
        notesPanel.hidden = false;
      }
    })
    .catch(() => {});
});
