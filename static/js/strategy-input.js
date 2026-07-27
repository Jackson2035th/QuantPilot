document.querySelectorAll("[data-example-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    const prompt = document.getElementById("id_prompt");
    if (!prompt) return;
    prompt.value = button.dataset.examplePrompt;
    prompt.focus();
  });
});
