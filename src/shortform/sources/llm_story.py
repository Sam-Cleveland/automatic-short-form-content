"""LLM-based story generator source adapter.

Generates original TIFU/AITA/Storytime content via an OpenAI-compatible or
Anthropic API, returning the same Post(title, body) that RedditSource produces.
"""

from __future__ import annotations

import json

from .base import Post

DEFAULT_SYSTEM_PROMPT = """\
You are an expert viral content creator specializing in Reddit-style short-form video stories \
for TikTok and Instagram Reels. You write in the authentic, conversational voice of Reddit's \
AITA, TIFU, and Storytime communities. Your stories are compelling, emotionally engaging, and \
perfectly paced for text-to-speech narration.\
"""

DEFAULT_STORY_PROMPT = """\
Write a compelling Reddit-style story (AITA, TIFU, or Storytime) optimized for TikTok video narration.

TITLE RULES (critical):
The title is the very first thing spoken aloud in the video — before the body. It IS the hook.
It must function as a spoken verbal grabber that makes a scrolling viewer stop dead. Write it \
as something you would actually SAY out loud to shock or intrigue someone, not just a descriptive \
headline. Strong title formulas: a moral dilemma stated bluntly ("AITA for telling my sister her \
fiancé hit on me at her bachelorette party?"), a confession with consequence hinted ("TIFU by \
accidentally sending my boss the wrong spreadsheet and now I might be fired"), or a cliffhanger \
premise ("I just found out my 'dead' biological father has been living 20 minutes away my entire life").

BODY RULES:
- Length: 350–450 words. At ~130 wpm TTS pace this yields a 2.5–3.5 minute TikTok — ideal for \
  story content.
- The body must NOT repeat or re-read the title. Assume the viewer already heard it. Open the \
  body mid-story, as if the title was your opening line and the body is what comes right after. \
  Use a natural bridge like "So here's what happened..." or jump straight into context.
- Opening: Include an age/gender identifier early (e.g., "I'm 26F and I've been with my partner \
  for three years..." or "I (34M) work at a small accounting firm...").
- Structure: brief context (2–3 sentences) → escalating conflict with 2–3 rising stakes → peak \
  moment → resolution or verdict.
- Voice: First-person, conversational, authentic Reddit tone. Use contractions, short punchy \
  sentences for dramatic beats, and natural speech patterns (e.g., "Like... what?", "I was \
  completely blindsided", "And that's when everything fell apart.").
- Emotional core: Build everything toward ONE dominant emotion — outrage, shock, empathy, or \
  satisfying justice. Every sentence serves that emotion.
- Mini-cliffhangers: End at least 2 paragraphs on a tension beat to keep viewers from scrolling.
- Ending: Close with either a clear verdict request ("So Reddit, AITA here?") or a resolution \
  that feels earned and emotionally satisfying — not abrupt.

Respond in valid JSON only — no preamble, no explanation, no markdown fences:
{"title": "...", "body": "..."}\
"""


class LLMStorySource:
    def __init__(self, cfg) -> None:  # cfg: LLMStoryConfig (avoid import cycle)
        self._cfg = cfg

    def fetch(self, topic: str = "") -> Post:
        messages = self._build_messages(topic)
        raw = self._call_api(messages)
        return self._parse_response(raw)

    def _build_messages(self, topic: str) -> list[dict]:
        content = self._cfg.story_prompt
        if topic and not topic.startswith("http"):
            content += f"\n\nTopic/theme hint: {topic}"
        return [{"role": "user", "content": content}]

    def _call_api(self, messages: list[dict]) -> str:
        if self._cfg.api_type == "openai":
            return self._call_openai(messages)
        if self._cfg.api_type == "anthropic":
            return self._call_anthropic(messages)
        raise ValueError(
            f"Unknown api_type: {self._cfg.api_type!r}. Choose 'openai' or 'anthropic'."
        )

    def _call_openai(self, messages: list[dict]) -> str:
        from openai import OpenAI  # noqa: PLC0415

        client = OpenAI(
            base_url=self._cfg.api_url or None,
            api_key=self._cfg.api_key or None,
        )
        response = client.chat.completions.create(
            model=self._cfg.model,
            messages=[
                {"role": "system", "content": self._cfg.system_prompt},
                *messages,
            ],
            max_tokens=self._cfg.max_tokens,
            temperature=self._cfg.temperature,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, messages: list[dict]) -> str:
        from anthropic import Anthropic  # noqa: PLC0415

        kwargs: dict = {"api_key": self._cfg.api_key or None}
        if self._cfg.api_url:
            kwargs["base_url"] = self._cfg.api_url
        client = Anthropic(**kwargs)
        response = client.messages.create(
            model=self._cfg.model,
            system=self._cfg.system_prompt,
            messages=messages,
            max_tokens=self._cfg.max_tokens,
        )
        return response.content[0].text

    def _parse_response(self, raw: str) -> Post:
        text = raw.strip()
        # Strip markdown code fences if the model ignores the instruction
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        return Post(title=data["title"], body=data["body"])
