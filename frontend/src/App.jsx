import { useState, useEffect } from 'react';
import { MapPin, DollarSign, Users, Clock, Coffee, Utensils, Leaf, Music, Film, Beer, ShoppingBag, LoaderCircle, AlertCircle, Sparkles, RefreshCw, Dice5, Star } from 'lucide-react';
import './App.css';

// --- Helper Components ---

const Header = () => (
  <header className="app-header">
    <div className="logo-container">
      <MapPin className="logo-icon" size={32} />
      <h1>OneStopOutings</h1>
    </div>
    <p>Your perfect day in Dublin, planned in seconds. | Created by Tanmay Kaushik</p>
  </header>
);

const ModeToggle = ({ mode, setMode }) => (
  <div className="mode-toggle">
    <button className={mode === 'surprise' ? 'active' : ''} onClick={() => setMode('surprise')}>
      <Dice5 size={16} />
      <span>Surprise Me</span>
    </button>
    <button className={mode === 'must-see' ? 'active' : ''} onClick={() => setMode('must-see')}>
      <Star size={16} />
      <span>Must See</span>
    </button>
  </div>
);

const PreferencesForm = ({ budget, setBudget, interests, toggleInterest, mode, setMode, onGetPlan, loading }) => {
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
        <label>Planning Mode</label>
        <ModeToggle mode={mode} setMode={setMode} />
      </div>

      <div className="form-group">
        <label htmlFor="budget">
          <DollarSign size={16} className="label-icon" />
          Your Budget
        </label>
        <div className="budget-control">
          <span>€20</span>
          <input type="range" id="budget" min="20" max="300" step="10" value={budget} onChange={(e) => setBudget(e.target.value)} />
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
              <button key={name} className={`interest-button ${isSelected ? 'selected' : ''}`} onClick={() => toggleInterest(name)}>
                {icon}
                <span>{name}</span>
              </button>
            );
          })}
        </div>
      </div>
      
      <button className="generate-button" onClick={onGetPlan} disabled={loading}>
        {loading ? <LoaderCircle size={20} className="spinner" /> : "Create My Outing"}
      </button>
    </div>
  );
};

const PlanDisplay = ({ plan, error, loading, onRegenerate, regeneratingIndex }) => {
  if (loading) {
    return <div className="plan-card skeleton"><div className="skeleton-line title"></div><div className="skeleton-line"></div><div className="skeleton-event"></div><div className="skeleton-event"></div><div className="skeleton-event"></div></div>;
  }
  if (error) {
    return <div className="plan-card error-card"><AlertCircle size={48} /><h3>An Error Occurred</h3><p>{error}</p></div>;
  }
  if (!plan) {
    return <div className="plan-card empty-card"><Sparkles size={48} /><h3>Your personalized plan will appear here</h3><p>Fill out your preferences and let our AI do the magic!</p></div>;
  }

  return (
    <div className="plan-card">
      <h2>Your Generated Plan</h2>
      <div className="plan-summary">
        <div className="summary-item"><DollarSign size={20} /><span>Total Cost: <strong>€{plan.total_cost}</strong></span></div>
        <div className="summary-item"><Clock size={20} /><span>Total Duration: <strong>{plan.total_duration} min</strong></span></div>
      </div>
      <div className="timeline">
        {plan.plan.map((event, index) => (
          <div key={index} className="itinerary-card">
            <div className="card-content">
              <div 
                className="image-placeholder" 
                style={{ backgroundImage: event.image_url ? `url(${event.image_url})` : 'none' }}
              ></div>
              <div className="event-details">
                <span className="event-type">{event.type}</span>
                <h4 className="event-name">{event.name}</h4>
              </div>
            </div>
            <div className="card-footer">
              <div className="footer-item">€{event.cost}</div>
              <div className="footer-item">{event.duration} min</div>
              <button className="regenerate-button" onClick={() => onRegenerate(index)} disabled={regeneratingIndex !== null}>
                {regeneratingIndex === index ? <LoaderCircle size={18} className="spinner" /> : <RefreshCw size={18} />}
              </button>
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
  const [mode, setMode] = useState('surprise');
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [regeneratingIndex, setRegeneratingIndex] = useState(null);

  useEffect(() => {
    document.body.className = '';
    document.body.classList.add(`theme-${mode}`);
  }, [mode]);

  const toggleInterest = (interest) => setInterests(prev => prev.includes(interest) ? prev.filter(i => i !== interest) : [...prev, interest]);

  const getPlan = async () => {
    if (interests.length === 0) { setError("Please select at least one interest."); return; }
    setLoading(true);
    setError(null);
    setPlan(null);

    const preferences = {
      budget: parseInt(budget),
      interests: interests,
      mode: mode,
    };

    try {
      // --- UPDATED: Use relative URL for the API call ---
      const response = await fetch('/api/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      });
      if (!response.ok) { const err = await response.json(); throw new Error(err.detail || 'Something went wrong'); }
      setPlan(await response.json());
    } catch (err) { setError(err.message); } 
    finally { setLoading(false); }
  };

  const handleRegenerate = async (indexToReplace) => {
    if (!plan || !plan.outing_id) {
      setError("Cannot regenerate without a valid plan. Please generate a new plan.");
      return;
    }

    setRegeneratingIndex(indexToReplace);
    setError(null);

    const payload = {
      current_plan: plan.plan,
      event_index_to_replace: indexToReplace,
      user_preferences: {
        budget: parseInt(budget),
        interests: interests,
        mode: mode,
      },
      outing_id: plan.outing_id,
    };

    try {
      // --- UPDATED: Use relative URL for the API call ---
      const response = await fetch('/api/regenerate-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) { const err = await response.json(); throw new Error(err.detail); }
      setPlan(await response.json());
    } catch (err) { setError(err.message); } 
    finally { setRegeneratingIndex(null); }
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
          mode={mode}
          setMode={setMode}
          onGetPlan={getPlan}
          loading={loading}
        />
        <PlanDisplay plan={plan} error={error} loading={loading} onRegenerate={handleRegenerate} regeneratingIndex={regeneratingIndex} />
      </main>
    </div>
  );
}

export default App;
