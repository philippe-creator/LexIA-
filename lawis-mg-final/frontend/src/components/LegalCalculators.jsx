import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Calculator, Briefcase, Clock, Wallet } from "lucide-react";
import { calculatorService, extractErrorMessage } from "../services/api";
import { useLanguage } from "../contexts/LanguageContext";
import { dateLocale } from "../i18n/dateLocale";

function ResultCard({ children }) {
  return <div className="calc-result">{children}</div>;
}

function SeveranceCalculator({ t, numLocale }) {
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
    } catch (e) { setError(extractErrorMessage(e, t("calculators.computeError"))); }
    finally { setLoading(false); }
  };

  return (
    <div className="calc-form">
      <div className="calc-fields">
        <div className="selector-group"><label>{t("calculators.grossSalary")}</label>
          <input type="number" min="0" className="select-input" value={salary} onChange={(e) => setSalary(e.target.value)} placeholder="6000" />
        </div>
        <div className="selector-group"><label>{t("calculators.seniority")}</label>
          <input type="number" min="0" step="0.5" className="select-input" value={years} onChange={(e) => setYears(e.target.value)} placeholder="8" />
        </div>
        <button className="compare-btn" onClick={compute} disabled={loading}>{loading ? t("calculators.computing") : t("calculators.compute")}</button>
      </div>
      {error && <div className="calc-error">{error}</div>}
      {result && (
        <ResultCard>
          <div className="calc-amount">{result.total_amount.toLocaleString(numLocale)} MAD</div>
          <p className="calc-detail">{t("calculators.hoursDetail", { hours: result.total_hours, rate: result.hourly_rate })}</p>
          <table className="data-table calc-breakdown">
            <thead><tr><th>{t("calculators.tranche")}</th><th>{t("calculators.years")}</th><th>{t("calculators.hoursPerYear")}</th><th>{t("calculators.totalHours")}</th></tr></thead>
            <tbody>{result.breakdown.map((b, i) => (
              <tr key={i}><td>{t("calculators.tranches", { n: i + 1 })}</td><td>{b.years_in_tranche}</td><td>{b.hours_per_year}h</td><td>{b.hours}h</td></tr>
            ))}</tbody>
          </table>
          <p className="calc-reference">{result.legal_reference}</p>
        </ResultCard>
      )}
    </div>
  );
}

function NoticePeriodCalculator({ t }) {
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
    } catch (e) { setError(extractErrorMessage(e, t("calculators.computeError"))); }
    finally { setLoading(false); }
  };

  return (
    <div className="calc-form">
      <div className="calc-fields">
        <div className="selector-group"><label>{t("calculators.category")}</label>
          <select className="select-input" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="employe">{t("calculators.employee")}</option>
            <option value="cadre">{t("calculators.executive")}</option>
          </select>
        </div>
        <div className="selector-group"><label>{t("calculators.seniority")}</label>
          <input type="number" min="0" step="0.5" className="select-input" value={years} onChange={(e) => setYears(e.target.value)} placeholder="3" />
        </div>
        <button className="compare-btn" onClick={compute} disabled={loading}>{loading ? t("calculators.computing") : t("calculators.compute")}</button>
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

function NetSalaryCalculator({ t, numLocale }) {
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
    } catch (e) { setError(extractErrorMessage(e, t("calculators.computeError"))); }
    finally { setLoading(false); }
  };

  return (
    <div className="calc-form">
      <div className="calc-fields">
        <div className="selector-group"><label>{t("calculators.grossSalary")}</label>
          <input type="number" min="0" className="select-input" value={gross} onChange={(e) => setGross(e.target.value)} placeholder="6000" />
        </div>
        <button className="compare-btn" onClick={compute} disabled={loading}>{loading ? t("calculators.computing") : t("calculators.compute")}</button>
      </div>
      {error && <div className="calc-error">{error}</div>}
      {result && (
        <ResultCard>
          <div className="calc-amount">{result.net_salary.toLocaleString(numLocale)} MAD {t("calculators.netSalary")}</div>
          <table className="data-table calc-breakdown">
            <tbody>
              <tr><td>{t("calculators.grossSalaryRow")}</td><td>{result.gross_salary.toLocaleString(numLocale)} MAD</td></tr>
              <tr><td>CNSS (4,48%)</td><td>- {result.cnss.toLocaleString(numLocale)} MAD</td></tr>
              <tr><td>AMO (2,26%)</td><td>- {result.amo.toLocaleString(numLocale)} MAD</td></tr>
              <tr><td>{t("calculators.irRate", { rate: Math.round(result.ir_rate * 100) })}</td><td>- {result.ir.toLocaleString(numLocale)} MAD</td></tr>
            </tbody>
          </table>
          <p className="calc-reference">{result.legal_reference}</p>
        </ResultCard>
      )}
    </div>
  );
}

export default function LegalCalculators() {
  const { t } = useTranslation();
  const { lang } = useLanguage();
  const numLocale = dateLocale(lang);
  const [tab, setTab] = useState("severance");
  const TABS = [
    { key: "severance", label: t("calculators.tabSeverance"), icon: Briefcase },
    { key: "notice", label: t("calculators.tabNotice"), icon: Clock },
    { key: "salary", label: t("calculators.tabSalary"), icon: Wallet },
  ];
  return (
    <div className="compare-container">
      <div className="compare-header"><Calculator size={20} /><h2>{t("calculators.title")}</h2></div>
      <p className="compare-subtitle">{t("calculators.subtitle")}</p>
      <div className="calc-tabs">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button key={key} className={`domain-chip ${tab === key ? "active" : ""}`} onClick={() => setTab(key)}>
            <Icon size={14} /><span>{label}</span>
          </button>
        ))}
      </div>
      {tab === "severance" && <SeveranceCalculator t={t} numLocale={numLocale} />}
      {tab === "notice" && <NoticePeriodCalculator t={t} />}
      {tab === "salary" && <NetSalaryCalculator t={t} numLocale={numLocale} />}
    </div>
  );
}
