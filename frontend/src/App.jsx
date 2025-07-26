import { useState } from 'react';
// NEW: Import icons from lucide-react
import { MapPin, DollarSign, Users, Clock, Coffee, Utensils, Leaf, Music, Film, Beer, ShoppingBag, LoaderCircle, AlertCircle, Sparkles } from 'lucide-react';
import './App.css';

// --- Helper Components ---

const Header = () => (
  <header className="app-header">
    <div className="logo-container">
      <MapPin className="logo-icon" size={32} />
      <h1>OneStopOutings</h1>
    </div>
    <p>Your personal Dublin day planner</p>
  </header>
);

const PreferencesForm = ({ budget, setBudget, interests, toggleInterest, onGetPlan, loading }) => {
  const availableInterests = [
    { name: "Food", icon: <Utensils size={20} /> },
    { name: "History", icon: <Leaf size={20} /> },
    { name: "Art", icon: <Sparkles size={20} /> },
    { name: "Music", icon: <Music size={20} /> },
    { name: "Nightlife", icon: <Beer size={20} /> },
    { name: "Shopping", icon: <ShoppingBag size={20} /> },
  ];

  return (
    <div className="preferences-card">
      <h2>Plan Your Perfect Day</h2>
      <p className="subtitle">Tell us what you're looking for.</p>
      
      <div className="form-group">
        <label htmlFor="budget">
          <DollarSign size={16} className="label-icon" />
          Your Budget
        </label>
        <div className="budget-control">
          <span>€20</span>
          <input
            type="range"
            id="budget"
            min="20"
            max="300"
            step="10"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          />
          <span>€300</span>
        </div>
        <div className="budget-display">€{budget}</div>
      </div>

      <div className="form-group">
        <label>
          <Users size={16} className="label-icon" />
          Your Interests
        </label>
        <div className="interests-container">
          {availableInterests.map(({ name, icon }) => {
            const isSelected = interests.includes(name);
            return (
              <button
                key={name}
                className={`interest-button ${isSelected ? 'selected' : ''}`}
                onClick={() => toggleInterest(name)}
              >
                {icon}
                <span>{name}</span>
              </button>
            );
          })}
        </div>
      </div>
      
      <button className="generate-button" onClick={onGetPlan} disabled={loading}>
        {loading ? (
          <LoaderCircle size={20} className="spinner" />
        ) : (
          "Create My Outing"
        )}
      </button>
    </div>
  );
};

const PlanDisplay = ({ plan, error, loading }) => {
  if (loading) {
    return (
      <div className="plan-card skeleton">
        <div className="skeleton-line title"></div>
        <div className="skeleton-line"></div>
        <div className="skeleton-event"></div>
        <div className="skeleton-event"></div>
        <div className="skeleton-event"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="plan-card error-card">
        <AlertCircle size={48} />
        <h3>An Error Occurred</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="plan-card empty-card">
        <Sparkles size={48} />
        <h3>Your personalized plan will appear here</h3>
        <p>Fill out your preferences and let our AI do the magic!</p>
      </div>
    );
  }

  const eventIcons = {
    "Breakfast": <Coffee size={24} />,
    "Lunch": <Utensils size={24} />,
    "Dinner": <Utensils size={24} />,
    "Activity": <Leaf size={24} />,
    "Pub": <Beer size={24} />,
    "Entertainment": <Film size={24} />,
    "Shopping": <ShoppingBag size={24} />,
    "Museum": <Leaf size={24}/>, // Placeholder
  };
  
  return (
    <div className="plan-card">
      <h2>Your Generated Plan</h2>
      <div className="plan-summary">
        <div className="summary-item">
          <DollarSign size={20} />
          <span>Total Cost: <strong>€{plan.total_cost}</strong></span>
        </div>
        <div className="summary-item">
          <Clock size={20} />
          <span>Total Duration: <strong>{plan.total_duration} min</strong></span>
        </div>
      </div>
      <div className="timeline">
        {plan.plan.map((event, index) => (
          <div key={index} className="event-card">
            <div className="event-icon">
              {eventIcons[event.type] || <Sparkles size={24} />}
            </div>
            <div className="event-details">
              <span className="event-type">{event.type}</span>
              <h4 className="event-name">{event.name}</h4>
              <div className="event-meta">
                <span>€{event.cost}</span>
                <span>{event.duration} min</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};


// --- Main App Component ---

function App() {
  const [budget, setBudget] = useState(50);
  const [interests, setInterests] = useState([]);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const toggleInterest = (interest) => {
    setInterests(prev => prev.includes(interest) ? prev.filter(i => i !== interest) : [...prev, interest]);
  };

  const getPlan = async () => {
    if (interests.length === 0) {
      setError("Please select at least one interest.");
      return;
    }
    setLoading(true);
    setError(null);
    setPlan(null);

    const preferences = {
      budget: parseInt(budget),
      interests: interests,
    };

    try {
      const response = await fetch('http://127.0.0.1:8000/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Something went wrong!');
      }
      const data = await response.json();
      setPlan(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <PreferencesForm
          budget={budget}
          setBudget={setBudget}
          interests={interests}
          toggleInterest={toggleInterest}
          onGetPlan={getPlan}
          loading={loading}
        />
        <PlanDisplay plan={plan} error={error} loading={loading} />
      </main>
    </div>
  );
}

export default App;
