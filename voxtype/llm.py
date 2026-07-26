import ollama

CHATBOT_INTRO_PHRASES = [
    "i'm here to help",
    "here is the cleaned",
    "here is your cleaned",
    "sure, here",
    "as an ai",
    "please go ahead and dictate",
    "how can i help",
]

class LLMEngine:
    def __init__(self, model: str, system_prompt: str,
                 command_prompt: str, temperature: float = 0.0):
        self.model = model
        self.system_prompt = system_prompt
        self.command_prompt = command_prompt
        self.temperature = temperature

    def cleanup(self, raw_text: str) -> str:
        """Dictation mode: clean up raw transcript into formatted text."""
        if not raw_text.strip():
            return ""
        try:
            print(f"[LLM] Sending to Ollama ({self.model})...")
            # Wrap transcript inside <transcript> tags to prevent LLM from answering as a chatbot
            user_content = f"<transcript>{raw_text}</transcript>"

            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content},
                ],
                options={"temperature": self.temperature},
            )
            result = response["message"]["content"].strip()

            # Check if LLM outputted a conversational chatbot response instead of transcript cleanup
            lower_res = result.lower()
            if any(phrase in lower_res for phrase in CHATBOT_INTRO_PHRASES):
                print(f"[LLM] Warning: Detected chatbot intro response. Falling back to raw transcript.")
                return raw_text

            print(f"[LLM] Cleaned output:\n{result}")
            return result
        except Exception as e:
            print(f"[LLM] Error calling Ollama: {e}")
            # Fallback: return raw transcript if LLM call fails
            return raw_text

    def command(self, selected_text: str, voice_command: str) -> str:
        """Command mode: transform selected text using voice command."""
        if not voice_command.strip():
            return selected_text
        try:
            prompt = f"EXISTING TEXT:\n{selected_text}\n\nCOMMAND: {voice_command}"
            print(f"[LLM] Command Mode prompt sent to Ollama ({self.model})...")
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.command_prompt},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.3},
            )
            result = response["message"]["content"].strip()
            print(f"[LLM] Command output:\n{result}")
            return result
        except Exception as e:
            print(f"[LLM] Error calling Ollama Command Mode: {e}")
            return selected_text

    def update_model(self, model: str) -> None:
        self.model = model

    def update_prompts(self, system_prompt: str, command_prompt: str) -> None:
        self.system_prompt = system_prompt
        self.command_prompt = command_prompt
