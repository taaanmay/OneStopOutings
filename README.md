# OneStopOutings - Personalized Outing Planner

## Project Vision

OneStopOutings is an intelligent application designed to eliminate the stress of planning a day out. Whether it's a casual evening with friends, a family trip, or a solo adventure, our app crafts personalized itineraries tailored to your unique tastes, budget, and schedule. By leveraging the power of Large Language Models (LLMs), we move beyond simple filters to provide truly dynamic, creative, and personalized suggestions for dining, activities, and entertainment.

## The Problem

Planning an outing can be overwhelming. It often involves juggling multiple apps and websites for restaurant reservations, event tickets, activity reviews, and directions. Factoring in personal preferences like dietary restrictions, budget limits, and specific interests for a group makes the task even more complex. OneStopOutings aims to solve this by consolidating the entire planning process into a single, seamless, and intelligent experience.

## Key Features

* **Intelligent Itinerary Generation:** Simply state your preferences in natural language (e.g., "a cheap day out with a movie and dinner, I'm a vegan") and get a complete, customized plan.
* **Dynamic Timeline View:** View your day's schedule in a simple, elegant timeline, complete with costs, durations, and locations for each event.
* **On-the-Fly Suggestions:** Don't like a specific event in your plan? Regenerate it with a single tap without affecting the rest of your outing.
* **Real-Time Recommendations:** Get instant suggestions for what to do next based on your current location and interests.
* **Budget & Preference Control:** Set your budget and select your interests to ensure every suggestion is a perfect fit.
* **Collaborative Planning:** Share your outing with friends and family to get their input and suggestions (Future Feature).

## Target Audience

* **Individuals & Couples:** Looking for new and interesting ways to spend their free time without the hassle of planning.
* **Groups of Friends:** Trying to coordinate plans that satisfy everyone's tastes and budgets.
* **Tourists & Visitors:** Seeking authentic, personalized experiences in a new city.
* **Families:** Planning activities that are enjoyable for both adults and children.

## Technology Stack & Architecture

This project is built on a modern, low-cost, and scalable serverless architecture. This approach minimizes operational overhead and ensures we only pay for the resources we use, which is ideal for a new application.

### High-Level Diagram
```plaintext
      +----------------+
      |      User      |
      | (Web/Mobile)   |
      +-------+--------+
              |
              | (HTTPS Request)
              v
+-------------+-------------------------------------------------+
| Frontend: React App (on Vercel/Netlify)                       |
+-------------+-------------------------------------------------+
              |
              | (REST API Calls)
              v
+-------------+-------------------------------------------------+
| Backend: FastAPI (on Vercel/AWS Lambda)                       |
+-------------+-------------------------------------------------+
      |       |                  |
      v       v                  v
+-----------+ +------------------+ +-----------------------------+
| Firestore | | Service Logic    | | Google Gemini API           |
| Database  | | (Business Rules) | | (LLM for personalization)   |
+-----------+ +------------------+ +-----------------------------+
```

### Core Components

1.  **Frontend (React):** A responsive and interactive user interface built with React. It will be hosted on **Vercel** or **Netlify** for fast global delivery and a seamless CI/CD pipeline.
2.  **Backend (FastAPI):** A high-performance Python backend responsible for handling user requests, business logic, and communication with other services. It will be deployed as **Serverless Functions** to ensure cost-efficiency and scalability.
3.  **Database (Cloud Firestore):** A flexible NoSQL database used to store user profiles, saved outings, preferences, and cached venue information. Its real-time capabilities will power future collaborative features.
4.  **LLM (Google Gemini API):** The intelligent core of the application. We use the **`gemini-2.0-flash`** model to understand user prompts, generate personalized plans, and provide dynamic suggestions, offering a powerful experience at a very low cost.

## How It Works

1.  A user opens the React app and describes their ideal outing.
2.  The frontend sends these preferences to the FastAPI backend.
3.  The backend constructs a detailed prompt and sends it to the Google Gemini API.
4.  Gemini returns a structured, personalized plan based on the user's request.
5.  The backend refines this plan with data from Firestore (e.g., user history, saved places) and sends the final itinerary to the user.
6.  The React app displays the complete outing in the interactive timeline, ready for the user to enjoy.
