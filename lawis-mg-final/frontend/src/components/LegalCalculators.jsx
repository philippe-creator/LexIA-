import React, { useState } from "react";
import { Calculator, Briefcase, Clock, Wallet } from "lucide-react";
import { calculatorService } from "../services/api";

const TABS = [
  { key: "severance", label: "Indemnité de licenciement", icon: Briefcase },
  { key: "notice", label: "Préavis légal", icon: Clock },
  { key: "salary", label: "Salaire net", icon: Wallet },
];

function ResultCard({ children }) {
  return <div className="calc-result">{children}</div>;
}

function SeveranceCalculator() {
  const [salary, setSalary] = useState("");
  const [years, setYears] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const compute = async () => {
    setError(null); setResult(null);
    if (!salary || !years) return;
    setLoading(true);
    try {
      const res = await calculatorService.severancePay({ monthly_salary: parseFloat(salary), years_of_service: parseFloat(years) });
      setResult(res.data);
    } catch (e) { setError(e.response?.data?.detail || "Erreur de calcul."); }
    finally { setLoading(false); }
  };

  return (
    <div className="calc-form">
      <div className="calc-fields">
        <div className="selector-group"><label>Salaire mensuel brut (MAD)</label>
          <input type="number" min="0" className="select-input" value={salary} onChange={(e) => setSalary(e.target.value)} placeholder="6000" />
        </div>
        <div className="selector-group"><label>Ancienneté (années)</label>
          <input type="number" min="0" step="0.5" className="select-input" value={years} onChange={(e) => setYears(e.target.value)} placeholder="8" />
        </div>
        <button className="compare-btn" onClick={compute} disabled={loading}>{loading ? "Calcul..." : "Calculer"}</button>
      </div>
      {error && <div className="calc-error">{error}</div>}
      {result && (
        <ResultCard>
          <div className="calc-amount">{result.total_amount.toLocaleString("fr-MA")} MAD</div>
          <p className="calc-detail">{result.total_hours}h de salaire × {result.hourly_rate} MAD/h (taux horaire)</p>
          <table className="data-table calc-breakdown">
            <thead><tr><th>Tranche</th><th>Années</th><th>Heures/an</th><th>Total heures</th></tr></thead>
            <tbody>{result.breakdown.map((b, i) => (
              <tr key={i}><td>Tranche {i + 1}</td><td>{b.years_in_tranche}</td><td>{b.hours_per_year}h</td><td>{b.hours}h</td></tr>
            ))}</tbody>
          </table>
          <p className="calc-reference">{result.legal_reference}</p>
        </ResultCard>
      )}
    </div>
  );
}

function NoticePeriodCalculator() {
  const [category, setCategory] = useState("employe");
  const [years, setYears] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const compute = async () => {
    setError(null); setResult(null);
    if (!years) return;
    setLoading(true);
    try {
      const res = await calculatorService.noticePeriod({ category, years_of_service: parseFloat(years) });
      setResult(res.data);
    } catch (e) { setError(e.response?.data?.detail || "Erreur de calcul."); }
    finally { setLoading(false); }
  };

  return (
    <div className="calc-form">
      <div className="calc-fields">
        <div className="selector-group"><label>Catégorie</label>
          <select className="select-input" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="employe">Employé</option>
            <option value="cadre">Cadre</option>
          </select>
        </div>
        <div className="selector-group"><label>Ancienneté (années)</label>
          <input type="number" min="0" step="0.5" className="select-input" value={years} onChange={(e) => setYears(e.target.value)} placeholder="3" />
        </div>
        <button className="compare-btn" onClick={compute} disabled={loading}>{loading ? "Calcul..." : "Calculer"}</button>
      </div>
      {error && <div className="calc-error">{error}</div>}
      {result && (
        <ResultCard>
          <div className="calc-amount">{result.notice_period}</div>
          <p className="calc-reference">{result.legal_reference}</p>
        </ResultCard>
      )}
    </div>
  );
}

function NetSalaryCalculator() {
  const [gross, setGross] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const compute = async () => {
    setError(null); setResult(null);
    if (!gross) return;
    setLoading(true);
    try {
      const res = await calculatorService.netSalary({ gross_salary: parseFloat(gross) });
      setResult(res.data);
    } catch (e) { setError(e.response?.data?.detail || "Erreur de calcul."); }
    finally { setLoading(false); }
  };

  return (
    <div className="calc-form">
      <div className="calc-fields">
        <div className="selector-group"><label>Salaire mensuel brut (MAD)</label>
          <input type="number" min="0" className="select-input" value={gross} onChange={(e) => setGross(e.target.value)} placeholder="6000" />
        </div>
        <button className="compare-btn" onClick={compute} disabled={loading}>{loading ? "Calcul..." : "Calculer"}</button>
      </div>
      {error && <div className="calc-error">{error}</div>}
      {result && (
        <ResultCard>
          <div className="calc-amount">{result.net_salary.toLocaleString("fr-MA")} MAD net</div>
          <table className="data-table calc-breakdown">
            <tbody>
              <tr><td>Salaire brut</td><td>{result.gross_salary.toLocaleString("fr-MA")} MAD</td></tr>
              <tr><td>CNSS (4,48%)</td><td>- {result.cnss.toLocaleString("fr-MA")} MAD</td></tr>
              <tr><td>AMO (2,26%)</td><td>- {result.amo.toLocaleString("fr-MA")} MAD</td></tr>
              <tr><td>IR ({Math.round(result.ir_rate * 100)}%)</td><td>- {result.ir.toLocaleString("fr-MA")} MAD</td></tr>
            </tbody>
          </table>
          <p className="calc-reference">{result.legal_reference}</p>
        </ResultCard>
      )}
    </div>
  );
}

export default function LegalCalculators() {
  const [tab, setTab] = useState("severance");
  return (
    <div className="compare-container">
      <div className="compare-header"><Calculator size={20} /><h2>Calculateurs juridiques</h2></div>
      <p className="compare-subtitle">Estimations fondées sur le Code du travail marocain (loi 65-99) — indicatives, ne remplacent pas une consultation professionnelle.</p>
      <div className="calc-tabs">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button key={key} className={`domain-chip ${tab === key ? "active" : ""}`} onClick={() => setTab(key)}>
            <Icon size={14} /><span>{label}</span>
          </button>
        ))}
      </div>
      {tab === "severance" && <SeveranceCalculator />}
      {tab === "notice" && <NoticePeriodCalculator />}
      {tab === "salary" && <NetSalaryCalculator />}
    </div>
  );
}
