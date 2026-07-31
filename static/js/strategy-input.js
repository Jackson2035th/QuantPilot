document.querySelectorAll("[data-example-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    // data-example-prompt stores the example text without hard-coding it in JavaScript.
    const prompt = document.getElementById("id_prompt");
    if (!prompt) return;
    prompt.value = button.dataset.examplePrompt;
    prompt.focus();
  });
});
