-- Active: 1776223846980@@localhost@3306
---
description: for any reasoning task for this project, load these instructions to provide context and guidelines for the agent's responses
# applyTo: 'Describe when these instructions should be loaded by the agent based on task context' # when provided, instructions will automatically be added to the request context when the pattern matches an attached file
---

<!-- Tip: Use /create-instructions in chat to generate content with agent assistance -->

you're given this project: https://github.com/soluchi07/ai110-module2show-pawpal-starter

Your project should do something useful with AI. For example:

* Summarize text or documents
* Retrieve information or data from a source
* Plan and complete a step-by-step task
* Help debug, classify, or explain something
To make your project more advanced, it must include at least one of the following AI features:
Feature What It Means Example Retrieval-Augmented Generation (RAG) Your AI looks up or retrieves information before answering. A study bot that searches notes before generating a quiz question. Agentic Workflow Your AI can plan, act, and check its own work. A coding assistant that writes, tests, and then fixes code automatically. Fine-Tuned or Specialized Model You use a model that’s been trained or adjusted for a specific task. A chatbot tuned to respond in a company’s tone of voice. Reliability or Testing System You include ways to measure or test how well your AI performs. A script that checks if your AI gives consistent answers.
The feature should be fully integrated into the main application logic. It is not enough to have standalone script; the feature must meaningfully change how the system behaves or processes information. For example, if you add RAG, your AI should actively use the retrieved data to formulate its response rather than just printing the data alongside a standard answer.
Also, make sure your project:

* Runs correctly and reproducibly: If someone follows your instructions, it should work.
* Includes logging or guardrails: Your code should track what it does and handle errors safely.
* Has clear setup steps: Someone else should be able to run it without guessing what to install.

We decided to go with this project:
PawPal+ AI Advisor with RAG
Extend PawPal+ so the AI doesn't just generate a schedule — it explains its choices by retrieving from a knowledge base of pet care facts.

How it works:

You build a small knowledge base of pet care guidelines (e.g., "dogs need 30–60 min of exercise daily," "cats shouldn't eat after 10pm before surgery")
When the schedule is generated, the AI does RAG: retrieves relevant facts from the knowledge base, then uses them to explain why each task was scheduled the way it was.

The AI also answers follow-up questions like "why is this walk scheduled first?" using retrieved context

Advanced feature: RAG — the retrieval step genuinely changes the AI's output, not just appended text.

Why it works well: PawPal+ already has scheduling logic; you're adding an explanation layer powered by retrieved knowledge. That's a clean, meaningful integration

Here's the exact plan:

Take your existing pawpal_system.py scheduling logic
Create a knowledge_base.py with ~20 pet care facts stored as a list of strings
Add a simple retrieval function (keyword or embedding-based similarity) that pulls the top 3 relevant facts given a task name
Pass those retrieved facts + the schedule into the Gemini API, prompting it to explain the schedule using those facts
Display the AI explanation in Streamlit alongside the schedule
Add logging (log what was retrieved and what the AI said) and a guardrail (if retrieval returns nothing relevant, say so rather than hallucinating)

This hits every requirement: useful AI task, RAG fully integrated into the response, logging, error handling, and clear setup steps.