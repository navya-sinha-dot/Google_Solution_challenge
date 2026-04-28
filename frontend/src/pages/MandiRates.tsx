import { useState, useEffect, useCallback } from 'react';
import { useTheme } from 'next-themes';
import { useLanguage } from '@/contexts/LanguageContext';
import { FarmBackground, GlassSection } from '@/components/FarmTheme';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import {
  TrendingUp, TrendingDown, Search, RefreshCw,
  ArrowUpDown, IndianRupee, MapPin, Calendar,
  Wheat, Loader2, Filter
} from 'lucide-react';

const API_URL = 'https://agentic-backend-lyx3.onrender.com';

interface MandiRate {
  state: string;
  district: string;
  market: string;
  commodity: string;
  variety: string;
  arrival_date: string;
  min_price: string;
  max_price: string;
  modal_price: string;
}

const STATES = [
  '', 'Andhra Pradesh', 'Bihar', 'Gujarat', 'Haryana',
  'Karnataka', 'Madhya Pradesh', 'Maharashtra', 'Punjab',
  'Rajasthan', 'Tamil Nadu', 'Telangana', 'Uttar Pradesh',
  'West Bengal',
];

export default function MandiRates() {
  const { t } = useLanguage();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [rates, setRates] = useState<MandiRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedState, setSelectedState] = useState('');
  const [selectedCommodity, setSelectedCommodity] = useState('');
  const [commodities, setCommodities] = useState<string[]>([]);
  const [sortField, setSortField] = useState<'modal_price' | 'commodity'>('commodity');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [lastRefresh, setLastRefresh] = useState<string>('');

  const fetchRates = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedState) params.set('state', selectedState);
      if (selectedCommodity) params.set('commodity', selectedCommodity);
      params.set('limit', '50');
      const res = await fetch(`${API_URL}/api/mandi/rates?${params}`);
      const data = await res.json();
      if (data.status === 'success') {
        setRates(data.rates || []);
        setLastRefresh(new Date().toLocaleTimeString());
      }
    } catch (err) {
      console.error('Failed to fetch mandi rates:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedState, selectedCommodity]);

  const fetchCommodities = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/mandi/commodities`);
      const data = await res.json();
      setCommodities(data.commodities || []);
    } catch { /* ignored */ }
  }, []);

  useEffect(() => { fetchCommodities(); }, [fetchCommodities]);
  useEffect(() => { fetchRates(); }, [fetchRates]);

  // Auto-refresh every 30 minutes
  useEffect(() => {
    const interval = setInterval(fetchRates, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchRates]);

  const filtered = rates
    .filter(r => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        r.commodity.toLowerCase().includes(q) ||
        r.market.toLowerCase().includes(q) ||
        r.state.toLowerCase().includes(q) ||
        r.district.toLowerCase().includes(q)
      );
    })
    .sort((a, b) => {
      if (sortField === 'modal_price') {
        const diff = Number(a.modal_price) - Number(b.modal_price);
        return sortDir === 'asc' ? diff : -diff;
      }
      const diff = a.commodity.localeCompare(b.commodity);
      return sortDir === 'asc' ? diff : -diff;
    });

  const toggleSort = (field: 'modal_price' | 'commodity') => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const cardBg = isDark ? 'rgba(20,35,20,0.7)' : 'rgba(255,255,255,0.85)';
  const cardBorder = isDark ? 'rgba(168,216,154,0.15)' : 'rgba(30,80,30,0.1)';
  const textPrimary = isDark ? '#A8D89A' : '#1B3A20';
  const textSecondary = isDark ? '#6A8A6A' : '#5A7A60';
  const accentGreen = '#2ECC71';

  return (
    <div style={{ minHeight: '100vh', position: 'relative' }}>
      <FarmBackground />

      <div style={{ position: 'relative', zIndex: 50 }}>
        <DashboardHeader lastUpdateSeconds={0} sensorNodeOnline={true} />
      </div>

      <main style={{ position: 'relative', zIndex: 10, maxWidth: '1400px', margin: '0 auto', padding: '32px 20px 60px' }}>

        {/* Page Title */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 style={{
            fontSize: '36px', fontWeight: 800,
            fontFamily: "'Nunito', sans-serif",
            color: textPrimary, marginBottom: '8px',
          }}>
            {t('mandi_title')}
          </h1>

          {lastRefresh && (
            <p style={{ fontSize: '12px', color: textPrimary, marginTop: '4px' }}>
              {t('Last_refreshed')}: {lastRefresh}
            </p>
          )}
        </div>

        {/* Filters Bar */}
        <GlassSection title="" noHeader>
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: '12px',
            alignItems: 'center', padding: '4px 0'
          }}>
            {/* Search */}
            <div style={{
              flex: '1 1 220px', display: 'flex', alignItems: 'center',
              background: isDark ? 'rgba(255,255,255,0.08)' : '#FFFFFF',
              borderRadius: '12px', padding: '0 14px',
              border: `1px solid ${cardBorder}`,
              boxShadow: isDark ? 'none' : '0 1px 3px rgba(0,0,0,0.05)',
            }}>
              <Search style={{ width: 18, height: 18, color: textSecondary, flexShrink: 0 }} />
              <input
                type="text"
                placeholder={t('mandi_search_placeholder')}
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{
                  flex: 1, padding: '12px 10px', border: 'none', outline: 'none',
                  background: 'transparent', color: textPrimary, fontSize: '14px',
                }}
              />
            </div>

            {/* State Filter */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              background: isDark ? 'rgba(255,255,255,0.08)' : '#FFFFFF',
              borderRadius: '12px', padding: '0 14px',
              border: `1px solid ${cardBorder}`,
              boxShadow: isDark ? 'none' : '0 1px 3px rgba(0,0,0,0.05)',
            }}>
              <MapPin style={{ width: 16, height: 16, color: textSecondary }} />
              <select
                value={selectedState}
                onChange={e => setSelectedState(e.target.value)}
                style={{
                  padding: '12px 4px', border: 'none', outline: 'none',
                  background: 'transparent', color: textPrimary, fontSize: '14px',
                  cursor: 'pointer',
                }}
              >
                <option value="">{t('mandi_all_states')}</option>
                {STATES.filter(Boolean).map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Commodity Filter */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              background: isDark ? 'rgba(255,255,255,0.08)' : '#FFFFFF',
              borderRadius: '12px', padding: '0 14px',
              border: `1px solid ${cardBorder}`,
              boxShadow: isDark ? 'none' : '0 1px 3px rgba(0,0,0,0.05)',
            }}>
              <Filter style={{ width: 16, height: 16, color: textSecondary }} />
              <select
                value={selectedCommodity}
                onChange={e => setSelectedCommodity(e.target.value)}
                style={{
                  padding: '12px 4px', border: 'none', outline: 'none',
                  background: 'transparent', color: textPrimary, fontSize: '14px',
                  cursor: 'pointer',
                }}
              >
                <option value="">{t('mandi_all_commodities')}</option>
                {commodities.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            {/* Refresh */}
            <button
              onClick={fetchRates}
              disabled={loading}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '12px 20px', borderRadius: '12px', border: 'none',
                background: accentGreen, color: '#fff', cursor: 'pointer',
                fontWeight: 700, fontSize: '14px', transition: 'all 0.2s',
                opacity: loading ? 0.7 : 1,
              }}
            >
              <RefreshCw style={{
                width: 16, height: 16,
                animation: loading ? 'spin 1s linear infinite' : 'none',
              }} />
              {t('advisor_refresh')}
            </button>
          </div>
        </GlassSection>

        {/* Summary Cards */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px', margin: '24px 0',
        }}>
          {[
            {
              label: t('mandi_total_entries'),
              value: filtered.length,
              icon: <Wheat style={{ width: 22, height: 22 }} />,
              color: '#2ECC71',
            },
            {
              label: t('mandi_highest_price'),
              value: filtered.length
                ? `₹${Math.max(...filtered.map(r => Number(r.modal_price))).toLocaleString()}`
                : '—',
              icon: <TrendingUp style={{ width: 22, height: 22 }} />,
              color: '#E74C3C',
            },
            {
              label: t('mandi_lowest_price'),
              value: filtered.length
                ? `₹${Math.min(...filtered.map(r => Number(r.modal_price))).toLocaleString()}`
                : '—',
              icon: <TrendingDown style={{ width: 22, height: 22 }} />,
              color: '#3498DB',
            },
            {
              label: t('mandi_avg_price'),
              value: filtered.length
                ? `₹${Math.round(filtered.reduce((s, r) => s + Number(r.modal_price), 0) / filtered.length).toLocaleString()}`
                : '—',
              icon: <IndianRupee style={{ width: 22, height: 22 }} />,
              color: '#F39C12',
            },
          ].map((card, i) => (
            <div key={i} style={{
              background: cardBg, borderRadius: '16px', padding: '20px',
              border: `1px solid ${cardBorder}`,
              backdropFilter: 'blur(12px)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <div style={{
                  width: 40, height: 40, borderRadius: '12px',
                  background: `${card.color}20`, display: 'flex',
                  alignItems: 'center', justifyContent: 'center', color: card.color,
                }}>
                  {card.icon}
                </div>
                <span style={{ fontSize: '13px', color: textSecondary, fontWeight: 600 }}>{card.label}</span>
              </div>
              <p style={{ fontSize: '24px', fontWeight: 800, color: textPrimary }}>{card.value}</p>
            </div>
          ))}
        </div>

        {/* Table */}
        <GlassSection title={t('mandi_commodity_prices')} icon="">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <Loader2 style={{ width: 32, height: 32, color: accentGreen, animation: 'spin 1s linear infinite', margin: '0 auto' }} />
              <p style={{ marginTop: '12px', color: textSecondary, fontWeight: 600 }}>{t('mandi_fetching')}</p>
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: textSecondary }}>
              <p style={{ fontSize: '18px', marginBottom: '8px' }}>{t('mandi_no_data')}</p>
              <p style={{ fontSize: '14px' }}>{t('mandi_try_filters')}</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 6px' }}>
                <thead>
                  <tr>
                    {[
                      { key: 'commodity', label: t('mandi_col_commodity') },
                      { key: 'variety', label: t('mandi_col_variety') },
                      { key: 'market', label: t('mandi_col_market') },
                      { key: 'state', label: t('mandi_col_state') },
                      { key: 'modal_price', label: t('mandi_col_modal_price') },
                      { key: 'min_price', label: t('mandi_col_min') },
                      { key: 'max_price', label: t('mandi_col_max') },
                      { key: 'arrival_date', label: t('mandi_col_date') },
                    ].map(col => (
                      <th
                        key={col.key}
                        onClick={() => {
                          if (col.key === 'commodity' || col.key === 'modal_price') {
                            toggleSort(col.key as any);
                          }
                        }}
                        style={{
                          padding: '12px 14px', textAlign: 'left', fontSize: '12px',
                          fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px',
                          color: textSecondary, whiteSpace: 'nowrap',
                          cursor: (col.key === 'commodity' || col.key === 'modal_price') ? 'pointer' : 'default',
                          userSelect: 'none',
                        }}
                      >
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          {col.label}
                          {(col.key === 'commodity' || col.key === 'modal_price') && (
                            <ArrowUpDown style={{ width: 12, height: 12, opacity: sortField === col.key ? 1 : 0.3 }} />
                          )}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((rate, idx) => {
                    const modal = Number(rate.modal_price);
                    const isHigh = modal > 3000;
                    return (
                      <tr key={idx} style={{
                        background: idx % 2 === 0
                          ? (isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.01)')
                          : 'transparent',
                        transition: 'background 0.2s',
                      }}>
                        <td style={{ padding: '14px', fontWeight: 700, color: textPrimary, fontSize: '14px' }}>
                          {rate.commodity}
                        </td>
                        <td style={{ padding: '14px', color: textSecondary, fontSize: '13px' }}>
                          {rate.variety}
                        </td>
                        <td style={{ padding: '14px', fontSize: '13px', color: textPrimary }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <MapPin style={{ width: 12, height: 12, color: accentGreen }} />
                            {rate.market}
                          </span>
                        </td>
                        <td style={{ padding: '14px', fontSize: '13px', color: textSecondary }}>
                          {rate.state}
                        </td>
                        <td style={{
                          padding: '14px', fontWeight: 800, fontSize: '15px',
                          color: isHigh ? '#E74C3C' : accentGreen,
                        }}>
                          ₹{Number(rate.modal_price).toLocaleString()}
                        </td>
                        <td style={{ padding: '14px', fontSize: '13px', color: textSecondary }}>
                          ₹{Number(rate.min_price).toLocaleString()}
                        </td>
                        <td style={{ padding: '14px', fontSize: '13px', color: textSecondary }}>
                          ₹{Number(rate.max_price).toLocaleString()}
                        </td>
                        <td style={{ padding: '14px', fontSize: '12px', color: textSecondary }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Calendar style={{ width: 12, height: 12 }} />
                            {rate.arrival_date}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </GlassSection>
      </main>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
