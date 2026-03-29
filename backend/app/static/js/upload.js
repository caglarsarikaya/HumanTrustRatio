(() => {
  const form       = document.getElementById("upload-form");
  const fileInput  = document.getElementById("file-input");
  const dropZone   = document.getElementById("drop-zone");
  const fileLabel  = document.getElementById("file-name");
  const submitBtn  = document.getElementById("submit-btn");
  const errorBox   = document.getElementById("error-box");

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) {
      fileLabel.textContent = fileInput.files[0].name;
      fileLabel.classList.remove("hidden");
      submitBtn.disabled = false;
    }
  });

  ["dragover", "dragenter"].forEach(evt =>
    dropZone.addEventListener(evt, e => {
      e.preventDefault();
      dropZone.classList.add("border-indigo-500");
    })
  );
  ["dragleave", "drop"].forEach(evt =>
    dropZone.addEventListener(evt, () =>
      dropZone.classList.remove("border-indigo-500")
    )
  );

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.classList.add("hidden");
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading\u2026";

    try {
      const body = new FormData();
      body.append("file", fileInput.files[0]);

      const res  = await fetch("/api/upload", { method: "POST", body });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      window.location.href = `/progress/${data.analysis_id}`;
    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Analyse Resume";
      errorBox.textContent = err.message;
      errorBox.classList.remove("hidden");
    }
  });
})();
