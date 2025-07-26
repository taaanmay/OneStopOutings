import { useState } from 'react';
import './App.css'; // We'll use the default styling for now

function App() {
  // State to hold the plan we get from the backend
  const [plan, setPlan] = useState(null);
  // State to show a loading message
  const [loading, setLoading] = useState(false);
  // State to hold any errors
  const [error, setError] = useState(null);

  // This function will be called when the user clicks the button
  const getPlan = async () => {
    setLoading(true);
    setError(null);
    setPlan(null);

    // The preferences we're sending to the backend.
    // For now, they are hardcoded. Later, we'll get them from a form.
    const preferences = {
      budget: 100,
      interests: ["food", "history", "art"],
    };

    try {
      // Make the API call to our FastAPI backend
      const response = await fetch('http://127.0.0.1:8000/plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(preferences),
      });

      if (!response.ok) {
        throw new Error('Something went wrong with the request!');
      }

      const data = await response.json();
      setPlan(data); // Save the received plan in our state

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>OneStopOutings Planner</h1>
        <p>Click the button to generate a sample outing plan!</p>
        
        {/* The button that triggers the API call */}
        <button onClick={getPlan} disabled={loading}>
          {loading ? 'Generating Plan...' : 'Get My Plan'}
        </button>

        {/* Display any errors that occur */}
        {error && <p style={{ color: 'red' }}>Error: {error}</p>}

        {/* Display the plan once we have it */}
        {plan && (
          <div style={{ marginTop: '2rem', textAlign: 'left', width: '80%' }}>
            <h2>Your Generated Plan:</h2>
            <p>Total Cost: €{plan.total_cost}</p>
            <p>Total Duration: {plan.total_duration} minutes</p>
            <hr />
            {plan.plan.map((event, index) => (
              <div key={index} style={{ border: '1px solid #ccc', padding: '10px', margin: '10px 0', borderRadius: '8px' }}>
                <h3>{event.type}: {event.name}</h3>
                <p>Cost: €{event.cost}</p>
                <p>Duration: {event.duration} min</p>
              </div>
            ))}
          </div>
        )}
      </header>
    </div>
  );
}

export default App;