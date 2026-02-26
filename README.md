# Python Console Agent

Run your own AI Console Agent with an Open Router API Key, OpenAI API and Python.

## AI Agent Definition

Definition: An autonomous software system that uses artificial intelligence to achieve specific goals by perceiving its environment, reasoning, planning, and taking actions (usually without human intervention). Unlike passive models, agents use tools, possess memory and can break down complex tasks into manageable steps.

## Key Features of an AI Agent:

* Memory: Able to maintain context from past interactions to improve future performance, compared to LLMS that have short-term memory
* Tool Usage: They can interact with external software, APIs, and databases to perform actions.
* Autonomy: Agents operate independently to complete tasks, rather than just providing answers.

---

## Setup & Installation

### Prerequisites
* Python. You can install it <a target="_blank" href="https://www.python.org/downloads/">here</a>
* Open Router API Key, and set it as an environment variable, `OPEN_ROUTER_API_KEY`.


> [!NOTE]  
> The Model uses Claude 3.5 Haiku Model. However, any model supported in Open Router Models can also be used.


### 1. Clone the repository
```git
git clone git@github.com:dayercher005/AI-Console-Agent.git
```

### 2. Install necessary dependencies 
```bash
pip install -U pydantic dotenv openai 
```

### 3. Run it on the console: 
```bash
python3 main.py
```
---

### Acknowledgements

* View the Open Router Documentation <a href="https://openrouter.ai/docs/quickstart" target="_blank">here</a>.
* View the OpenAI API Documentation <a target="_blank" href="https://developers.openai.com/api/docs">here</a>
