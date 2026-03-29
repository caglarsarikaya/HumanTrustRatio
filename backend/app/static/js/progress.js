(() => {
  const root        = document.getElementById("progress-root");
  const bar         = document.getElementById("progress-bar");
  const counter     = document.getElementById("step-counter");
  const errorBox    = document.getElementById("error-box");
  const analysisId  = root.dataset.id;
  const totalSteps  = 4;

  const SPINNER_SVG =
    '<svg class="animate-spin h-5 w-5 text-brand-500" fill="none" viewBox="0 0 24 24">' +
      '<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>' +
      '<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>' +
    '</svg>';

  const CHECK_SVG =
    '<svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">' +
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>' +
    '</svg>';

  let completedSteps = 0;

  function getCard(step) {
    return document.querySelector(`.step-card[data-step="${step}"]`);
  }

  function setStepRunning(step) {
    const card   = getCard(step);
    const icon   = card.querySelector(".step-icon");
    const status = card.querySelector(".step-status");

    card.classList.remove("border-gray-200", "bg-white");
    card.classList.add("border-brand-300", "bg-brand-50", "shadow-md");
    icon.classList.remove("bg-gray-100", "text-gray-400");
    icon.classList.add("bg-brand-500", "text-white");
    icon.innerHTML = SPINNER_SVG;
    status.textContent = "Running";
    status.classList.remove("text-gray-400");
    status.classList.add("text-brand-600", "font-medium");

    counter.textContent = `Step ${step} of ${totalSteps} — ${card.querySelector(".font-semibold").textContent}`;
  }

  function setStepDone(step) {
    const card   = getCard(step);
    const icon   = card.querySelector(".step-icon");
    const status = card.querySelector(".step-status");

    card.classList.remove("border-brand-300", "bg-brand-50", "shadow-md");
    card.classList.add("border-mint-300", "bg-mint-50");
    icon.classList.remove("bg-brand-500");
    icon.classList.add("bg-mint-500");
    icon.innerHTML = CHECK_SVG;
    status.textContent = "Done";
    status.classList.remove("text-brand-600");
    status.classList.add("text-mint-600");

    completedSteps = Math.max(completedSteps, step);
    bar.style.width = `${(completedSteps / totalSteps) * 100}%`;
  }

  function handleEvent(msg) {
    if (msg.event === "step_update") {
      if (msg.status === "running") {
        setStepRunning(msg.step);
      } else if (msg.status === "done") {
        setStepDone(msg.step);
      }
    } else if (msg.event === "complete") {
      bar.style.width = "100%";
      bar.classList.remove("bg-brand-500");
      bar.classList.add("bg-mint-500");
      counter.textContent = "Analysis complete — redirecting\u2026";

      setTimeout(() => {
        window.location.href = `/result/${msg.analysis_id}`;
      }, 1200);
    } else if (msg.event === "error") {
      errorBox.textContent = msg.detail || "Something went wrong.";
      errorBox.classList.remove("hidden");
      counter.textContent = "An error occurred";
      bar.classList.remove("bg-brand-500");
      bar.classList.add("bg-red-400");
    }
  }

  const evtSource = new EventSource(`/api/progress/${analysisId}`);

  evtSource.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      handleEvent(msg);
      if (msg.event === "complete" || msg.event === "error") {
        evtSource.close();
      }
    } catch (err) {
      console.error("Failed to parse SSE message", err);
    }
  };

  evtSource.onerror = () => {
    evtSource.close();
    errorBox.textContent = "Lost connection to server. Please refresh the page.";
    errorBox.classList.remove("hidden");
  };
})();
