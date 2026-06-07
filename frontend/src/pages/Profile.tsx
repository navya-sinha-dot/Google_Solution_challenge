import { useState, useEffect } from "react";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { FarmBackground } from "@/components/FarmTheme";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { UserCircle, MapPin, LayoutGrid, Wheat, ShieldCheck, ExternalLink, Loader2, Pencil, Check, X, Cpu, Wifi, WifiOff, ShoppingCart } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { motion } from "framer-motion";

const API_URL = import.meta.env.VITE_API_URL || '';

const LOCAL_SCHEMES = [
  {
    scheme_name: "PM-Kisan Samman Nidhi",
    description: "Direct income support of ₹6,000 per year in three instalments to all landholding farmer families.",
    required_docs: ["Aadhar Card", "Bank Passbook", "Land Ownership Proof"],
    link: "https://pmkisan.gov.in/",
    source: "Government Scheme",
  },
  {
    scheme_name: "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
    description: "Financial support to farmers suffering crop loss or damage due to natural calamities, pests and diseases.",
    required_docs: ["Aadhar Card", "Sowing Certificate", "Bank Passbook"],
    link: "https://pmfby.gov.in/",
    source: "Government Scheme",
  },
  {
    scheme_name: "Soil Health Card Scheme",
    description: "Helps farmers understand the nutrient status of their soil and use fertilizers judiciously to reduce costs.",
    required_docs: ["Aadhar Card", "Soil Sample Collection Report"],
    link: "https://soilhealth.dac.gov.in/",
    source: "Government Scheme",
  },
  {
    scheme_name: "Kisan Credit Card (KCC)",
    description: "Provides farmers with timely and adequate credit for cultivation needs and short-term credit requirements.",
    required_docs: ["Aadhar Card", "Land Records", "Passport Size Photograph"],
    link: "https://www.myscheme.gov.in/schemes/kcc",
    source: "Government Scheme",
  },
  {
    scheme_name: "Paramparagat Krishi Vikas Yojana (PKVY)",
    description: "Promotes organic farming through a cluster approach and PGS certification to improve soil health.",
    required_docs: ["Aadhar Card", "Cluster Registration Proof"],
    link: "https://pgsindia-ncof.dac.gov.in/pkvy/",
    source: "Government Scheme",
  },
  {
    scheme_name: "National Mission for Sustainable Agriculture (NMSA)",
    description: "Promotes sustainable agriculture through climate-resilient practices and resource conservation technologies.",
    required_docs: ["Aadhar Card", "Soil Health Card", "Bank Passbook"],
    link: "https://nmsa.dac.gov.in/",
    source: "Government Scheme",
  },
];

export default function Profile() {
  const [profileData, setProfileData] = useState({
    name: "",
    land_size_acres: "",
    crops: [] as string[],
    location: ""
  });
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ name: "", land_size_acres: "", location: "", crops: "" });
  const [saving, setSaving] = useState(false);
  const [schemes, setSchemes] = useState<any[]>([]);
  const [schemesLoading, setSchemesLoading] = useState(true);
  const [hwConnecting, setHwConnecting] = useState(false);
  const { toast } = useToast();
  const { t } = useLanguage();
  const { hardwareConnected, connectHardware, disconnectHardware } = useAuth();
  const navigate = useNavigate();

  const handleConnectHardware = async () => {
    setHwConnecting(true);
    await new Promise(r => setTimeout(r, 1500));
    connectHardware('AGRISENSE-WS01');
    setHwConnecting(false);
    toast({ title: "Hardware Connected", description: "AgriSense WS01 is now paired to your account." });
  };

  useEffect(() => {
    // Show local schemes immediately
    setSchemes(LOCAL_SCHEMES);

    // Load cached profile from localStorage immediately (no flicker)
    const cachedName = localStorage.getItem("user_name") || "";
    const cachedLand = localStorage.getItem("user_land_size") || "";
    const cachedLocation = localStorage.getItem("user_location") || "";
    const cachedCrops = localStorage.getItem("user_crops") || "";
    if (cachedName || cachedLocation) {
      setProfileData({
        name: cachedName,
        land_size_acres: cachedLand,
        location: cachedLocation,
        crops: cachedCrops ? cachedCrops.split(",").map(c => c.trim()).filter(Boolean) : [],
      });
      fetchSchemes(cachedLand, cachedLocation);
    }

    // Then try to sync fresher data from the backend DB
    const fetchProfile = async () => {
      try {
        const phone = localStorage.getItem("user_phone");
        if (!phone) { setSchemesLoading(false); return; }
        const response = await fetch(`${API_URL}/api/profile?phone=${encodeURIComponent(phone)}`);
        const data = await response.json();
        if (data.status === "success" && data.profile && data.profile.name) {
          const p = data.profile;
          setProfileData({
            name: p.name || cachedName,
            land_size_acres: p.land_size_acres || cachedLand,
            location: p.location || cachedLocation,
            crops: p.crops?.length ? p.crops : cachedCrops.split(",").map((c: string) => c.trim()).filter(Boolean),
          });
          // Update localStorage cache with fresher DB data
          if (p.name) localStorage.setItem("user_name", p.name);
          if (p.land_size_acres) localStorage.setItem("user_land_size", String(p.land_size_acres));
          if (p.location) localStorage.setItem("user_location", p.location);
          if (p.crops?.length) localStorage.setItem("user_crops", p.crops.join(", "));
          fetchSchemes(p.land_size_acres || cachedLand, p.location || cachedLocation);
        } else {
          setSchemesLoading(false);
        }
      } catch {
        setSchemesLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const fetchSchemes = async (landSize: any, loc: any) => {
    setSchemesLoading(true);
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);

      const response = await fetch(
        `${API_URL}/api/schemes`,
        { signal: controller.signal }
      );
      clearTimeout(timeout);

      if (!response.ok) throw new Error("HTTP " + response.status);

      const data = await response.json();
      const backendSchemes = Array.isArray(data)
        ? data
        : Array.isArray(data?.schemes)
          ? data.schemes
          : [];

      const localDocsByScheme = new Map(
        LOCAL_SCHEMES.map(item => [item.scheme_name.toLowerCase(), item.required_docs])
      );

      const normalized = backendSchemes
        .filter((scheme: any) => scheme?.scheme_name)
        .map((scheme: any) => ({
          scheme_name: scheme.scheme_name,
          description: scheme.benefit_description || scheme.description || "Government scheme details available.",
          required_docs: Array.isArray(scheme.required_docs)
            ? scheme.required_docs
            : localDocsByScheme.get(String(scheme.scheme_name).toLowerCase()) || [],
          link: scheme.official_url || scheme.link || "https://www.myscheme.gov.in/",
          source: scheme.source || scheme.status || "Government Scheme",
        }));

      setSchemes(normalized.length > 0 ? normalized : LOCAL_SCHEMES);
    } catch {
      // Network error or timeout — fall back to local schemes silently
      setSchemes(LOCAL_SCHEMES);
    } finally {
      setSchemesLoading(false);
    }
  };

  const startEdit = () => {
    setEditForm({
      name: profileData.name,
      land_size_acres: profileData.land_size_acres,
      location: profileData.location,
      crops: profileData.crops.join(", "),
    });
    setEditing(true);
  };

  const saveProfile = async () => {
    setSaving(true);
    const phone = localStorage.getItem("user_phone") || "";
    const cropsArr = editForm.crops.split(",").map(c => c.trim()).filter(Boolean);

    // Save to localStorage immediately
    localStorage.setItem("user_name", editForm.name);
    localStorage.setItem("user_land_size", editForm.land_size_acres);
    localStorage.setItem("user_location", editForm.location);
    localStorage.setItem("user_crops", editForm.crops);

    // Update UI immediately
    setProfileData({
      name: editForm.name,
      land_size_acres: editForm.land_size_acres,
      location: editForm.location,
      crops: cropsArr,
    });
    setEditing(false);

    // Persist to backend
    try {
      await fetch(`${API_URL}/api/profile/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: editForm.name, phone, land_size_acres: editForm.land_size_acres, location: editForm.location, crops: cropsArr }),
      });
      toast({ title: "Profile saved", description: "Your details have been updated." });
    } catch {
      toast({ title: "Saved locally", description: "Could not reach server, but your details are saved on this device." });
    }

    fetchSchemes(editForm.land_size_acres, editForm.location);
    setSaving(false);
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <FarmBackground />
      <div className="relative z-50">
        <DashboardHeader lastUpdateSeconds={0} sensorNodeOnline={true} />
      </div>

      <div className="relative z-40 max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-10 text-center"
        >
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
            {t('profile_title')}
          </h1>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* LEFT: PROFILE INFO + HARDWARE */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            <Card className="sticky top-24 border-border shadow-md bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/75">
              <CardHeader className="pb-4 border-b border-border/50">
                <CardTitle className="text-xl flex items-center justify-between">
                  <span className="flex items-center gap-3"><UserCircle className="w-6 h-6 text-primary" /> {t('Profile')}</span>
                  {!editing && (
                    <button onClick={startEdit} className="text-muted-foreground hover:text-primary transition-colors">
                      <Pencil className="w-4 h-4" />
                    </button>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-4">
                {editing ? (
                  <div className="space-y-3">
                    {[
                      { label: t('signup_full_name'), key: "name", placeholder: "e.g. Rajan Kumar" },
                      { label: t('signup_land_size'), key: "land_size_acres", placeholder: "e.g. 5.5" },
                      { label: t('location'), key: "location", placeholder: "e.g. Maharashtra" },
                      { label: t('signup_crops'), key: "crops", placeholder: "e.g. Wheat, Rice" },
                    ].map(({ label, key, placeholder }) => (
                      <div key={key} className="space-y-1">
                        <label className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">{label}</label>
                        <input
                          value={editForm[key as keyof typeof editForm]}
                          onChange={e => setEditForm(f => ({ ...f, [key]: e.target.value }))}
                          placeholder={placeholder}
                          className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm outline-none focus:ring-2 focus:ring-primary/40"
                        />
                      </div>
                    ))}
                    <div className="flex gap-2 pt-2">
                      <Button onClick={saveProfile} disabled={saving} className="flex-1 gap-2">
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} {t('Save')}
                      </Button>
                      <Button variant="outline" onClick={() => setEditing(false)} className="flex-1 gap-2">
                        <X className="w-4 h-4" /> {t('Cancel')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    {[
                      { label: t('signup_full_name'), icon: <UserCircle className="w-5 h-5 text-primary/70" />, value: profileData.name },
                      { label: t('profile_land_size'), icon: <LayoutGrid className="w-5 h-5 text-primary/70" />, value: profileData.land_size_acres ? `${profileData.land_size_acres} Acres` : "" },
                      { label: t('location'), icon: <MapPin className="w-5 h-5 text-primary/70" />, value: profileData.location },
                      { label: t('profile_crops_grown'), icon: <Wheat className="w-5 h-5 text-primary/70" />, value: profileData.crops.length > 0 ? profileData.crops.join(", ") : "" },
                    ].map(({ label, icon, value }) => (
                      <div key={label} className="space-y-1">
                        <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">{label}</span>
                        <div className="flex items-center gap-3 text-base font-medium text-foreground">
                          {icon}
                          {value || <span className="text-muted-foreground italic text-sm cursor-pointer hover:text-primary" onClick={startEdit}>{t('profile_tap_to_add')}</span>}
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </CardContent>
            </Card>

            {/* HARDWARE CONNECTION CARD */}
            <Card className="border-border shadow-md bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/75">
              <CardHeader className="pb-4 border-b border-border/50">
                <CardTitle className="text-xl flex items-center gap-3">
                  <Cpu className="w-6 h-6 text-primary" />
                  Hardware Device
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-5 space-y-4">
                {hardwareConnected ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-primary/10 border border-primary/20">
                      <div className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse" />
                      <div>
                        <p className="text-sm font-bold text-foreground">AgriSense WS01</p>
                        <p className="text-xs text-muted-foreground">FPGA Weather Station • Live</p>
                      </div>
                      <Wifi className="w-4 h-4 text-primary ml-auto" />
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full gap-2 text-destructive border-destructive/30 hover:bg-destructive/10"
                      onClick={() => { disconnectHardware(); toast({ title: "Hardware Disconnected" }); }}
                    >
                      <WifiOff className="w-4 h-4" /> Disconnect
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-muted/50 border border-border">
                      <WifiOff className="w-4 h-4 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">No device connected</p>
                    </div>
                    <Button
                      className="w-full gap-2"
                      onClick={handleConnectHardware}
                      disabled={hwConnecting}
                    >
                      {hwConnecting
                        ? <><Loader2 className="w-4 h-4 animate-spin" /> Connecting...</>
                        : <><Wifi className="w-4 h-4" /> Connect AgriSense WS01</>
                      }
                    </Button>
                    <Button
                      variant="outline"
                      className="w-full gap-2"
                      onClick={() => navigate('/buy-hardware')}
                    >
                      <ShoppingCart className="w-4 h-4" /> Buy New Hardware
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* RIGHT: SCHEMES & DOCS */}
          <div className="lg:col-span-8">
            <Card className="border-border shadow-md bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/75">
              <CardHeader className="flex flex-row items-center justify-between pb-6 border-b border-border/50">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="w-7 h-7 text-primary" />
                  <div>
                    <CardTitle className="text-2xl flex items-center gap-2">
                      {t('Recommended Schemes')}
                      {schemesLoading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
                    </CardTitle>

                  </div>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={schemesLoading}
                  onClick={() => fetchSchemes(profileData.land_size_acres, profileData.location)}
                >
                  {schemesLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : t('advisor_refresh')}
                </Button>
              </CardHeader>

              <CardContent className="pt-6">
                {schemesLoading && schemes.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <Loader2 className="w-10 h-10 animate-spin text-primary/50 mb-4" />
                    <p className="text-muted-foreground font-medium">{t('profile_loading_schemes')}</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {schemes.map((scheme, i) => (
                      <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.1 * i }}
                        key={i}
                      >
                        <div className="relative p-6 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow overflow-hidden">
                          <div className="absolute top-0 left-0 w-1.5 h-full bg-primary" />

                          <div className="space-y-3 pl-2">
                            <div className="flex items-center justify-between gap-2">
                              <h4 className="text-xl font-bold tracking-tight text-foreground">
                                {scheme.scheme_name}
                              </h4>

                            </div>
                            <p className="text-muted-foreground text-sm leading-relaxed">
                              {scheme.description}
                            </p>

                            <div className="bg-muted/40 rounded-lg p-4 mt-4 border border-border/50">
                              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                                {t('profile_required_docs')}
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {scheme.required_docs.map((doc: string, idx: number) => (
                                  <span key={idx} className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary border border-primary/20">
                                    {doc}
                                  </span>
                                ))}
                              </div>
                            </div>

                            <div className="pt-4">
                              <Button
                                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm flex items-center justify-center gap-2"
                                onClick={() => window.open(scheme.link, "_blank")}
                              >
                                <ExternalLink className="w-4 h-4" /> {t('profile_apply_btn')}
                              </Button>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
