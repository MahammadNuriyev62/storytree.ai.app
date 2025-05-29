# 🌳 StoryTree.ai: Infinite AI-Powered Interactive Adventures 📖

StoryTree.ai is a platform for crafting and exploring dynamic, interactive narratives 🤖. Powered by Large Language Models (LLMs), it employs a unique **lazy generation** technique. This allows for the creation of immense, branching story trees 🌲 where every user choice carves a unique path through the adventure.

## 🧠 Core Concept: Lazy Story Generation

Traditional interactive story generation faces a significant challenge: combinatorial explosion 💥. A story with a depth of 50 scenes, each offering just two choices, would necessitate the pre-generation of 2^50 (over a quadrillion!) scenes 🤯. StoryTree.ai elegantly sidesteps this challenge:

- **✨ On-Demand Creation:** Scenes and choices are materialized _only_ when a player's decision necessitates them. This means only the explored paths exist in the database. 🚶‍♂️
- **🔮 LLM as a Compact Store:** The underlying LLM (currently supporting Qwen3 4B via Ollama 🦙) functions as an implicit, compact representation of a virtually infinite number of potential story branches and scenes.
- **💾 Database Caching:** Once a scene or choice is generated, it is persisted in a database (SQLite). This ensures swift retrieval for subsequent players or replays along the same path.
- **Thread Safety:** TODO
- **⏳ Seamless Experience:** Each choice includes a `loading_text` field. This text is displayed to the user 🤔 while the next scene is being generated in the background, maintaining engagement and masking potential latency.

This lazy approach facilitates the creation of stories with remarkable depth (50-100 scenes or more) and branching complexity, offering genuine replayability and a sense of unique agency.

## 🏗️ Architecture & Tech Stack

StoryTree.ai is built with a modern, efficient technology stack:

- **🚀 Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python) provides a high-performance, asynchronous API framework.
- **📚 Database & ORM:** [SQLModel](https://sqlmodel.tiangolo.com/) (built on Pydantic and SQLAlchemy) handles data modeling, validation, and interaction with the [SQLite](https://www.sqlite.org/index.html) database.
- **🤖 LLM Integration:** [Ollama](https://ollama.com/) facilitates interaction with locally-run Large Language Models.
- **🎨 Frontend Templating:** [Jinja2](https://jinja.palletsprojects.com/en/3.1.x/) renders the user interface on the server-side.
- **💨 Styling:** [TailwindCSS](https://tailwindcss.com/) combined with custom CSS delivers a clean, responsive, and visually appealing user experience.

## 🔌 API Endpoints (`/api`)

The core functionality is exposed via a set of RESTful API endpoints:

1.  **`POST /stories`**: ✍️ **Create a New Story**
    - Accepts a user-provided `description`, desired `n_scenes`, and `choices_weights` (probabilities for 1, 2, or 3+ choices per scene).
    - Leverages the LLM to generate comprehensive story `metadata` (title, description, characters, themes, worldview, emojis).
    - Generates the `first_introduction_scene` along with its initial choice (Acts as a one-shot prompt for the LLM to generate proceeding scenes).
    - Persists the initial story structure and root scene to the database.
2.  **`GET /stories/description`**: 💡 **Generate Story Description**
    - Provides a 2-3 sentence story concept for users seeking inspiration.
3.  **`GET /stories/{story_id}/scene`**: 🎬 **Fetch/Generate Scene**
    - The powerhouse of the lazy generation system.
    - If `choice_id` is provided, it attempts to retrieve the `next_scene`.
    - If no `choice_id` is given, it finds the "root" or current leaf scene for the story.
    - **Crucially:** If the requested `next_scene` has not been generated yet (`text` is `None`), it triggers the `continue_story_branch` function. This function:
      - Constructs the story history (scenes + choices made).
      - Prompts the LLM to generate the `text` for the current scene and its subsequent `choices`.
      <!-- - Creates placeholder `Scene` objects for the new choices. -->
      - Persists the newly generated content to the database.
      - Returns the now-complete scene.
4.  **`GET /stories`**: 📚 **List All Stories**
    - Retrieves a summary list of all stories currently in the database.
5.  **`GET /stories/{story_id}`**: ℹ️ **Get Story Details**
    - Fetches and returns the complete metadata for a specific story.

## 🖥️ Frontend Interface

A user-friendly web interface allows players to interact with the stories:

- **🏠 `/` (Home):** A welcoming landing page showcasing the platform and offering entry points.
- **📖 `/stories`:** The story library, displaying available adventures with options to start new or continue existing ones (using local storage for progress).
- **ℹ️ `/stories/{story_id}`:** A details page presenting the story's metadata, characters, and themes before diving in.
- **▶️ `/stories/{story_id}/play`:** The main gameplay screen, displaying the current scene text and available choices.
- **✨ `/create`:** An intuitive form for users to define their own story concepts and parameters.

## Deployment (TODO)

### Manually

To run StoryTree.ai locally, clone the repository and follow these steps:

1. Make sure you have ollama and qwen3 4B installed

```bash
curl -fsSL https://ollama.com/install.sh | sh # Linux
```

```bash
ollama pull qwen3:4b
```

2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

3. Start the FastAPI server:

```bash
uvicorn main:app --reload
```

### Docker

TODO

StoryTree.ai offers a framework for exploring the potential of LLMs in creating deeply engaging, user-driven interactive fiction. 🌟
