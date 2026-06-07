import { useState } from "react";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { FarmBackground, GlassSection } from "@/components/FarmTheme";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Mic, Search, Tractor, Users, Wheat } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const API_URL = import.meta.env.VITE_API_URL || '';

export default function Marketplace() {
  const [needType, setNeedType] = useState("labor");
  const [location, setLocation] = useState("Punjab");
  const [matches, setMatches] = useState<any[]>([]);
  const [voiceSearchActive, setVoiceSearchActive] = useState(false);
  const { toast } = useToast();

  const handleSearch = async () => {
    try {
      const response = await fetch(`${API_URL}/api/marketplace/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ need_type: needType, location })
      });
      const data = await response.json();
      if (data.status === "success") {
        setMatches(data.matches);
        if (data.matches.length === 0) {
          toast({ title: "No exact matches", description: "Try changing your location or need." });
        }
      }
    } catch {
      toast({ title: "Search failed", variant: "destructive" });
    }
  };

  const handleVoiceSearch = () => {
    setVoiceSearchActive(true);
    toast({ title: "Listening...", description: "E.g. 'I need a tractor in Punjab'" });
    
    // Mocking an STT extraction of location and need
    setTimeout(() => {
      setVoiceSearchActive(false);
      setNeedType("equipment");
      setLocation("Punjab");
      toast({ title: "Voice Captured", description: "Parsed: Equipment in Punjab. Searching..." });
      // Call search instantly after voice parsing
      setTimeout(() => {
        handleSearch();
      }, 500);
    }, 3000);
  };

  return (
    <div style={{ minHeight: "100vh", position: "relative" }}>
      <FarmBackground />
      <div style={{ position: "relative", zIndex: 50 }}>
        <DashboardHeader lastUpdateSeconds={0} sensorNodeOnline={true} />
      </div>

      <div style={{ padding: "2rem", maxWidth: "1200px", margin: "0 auto", position: "relative", zIndex: 40 }}>
        <h1 className="text-3xl font-bold text-emerald-900 dark:text-white mb-6">Agri Marketplace & Labor Match</h1>
        
        <GlassSection style={{ padding: "2rem", marginBottom: "2rem" }}>
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1 w-full relative">
               <label className="text-sm font-semibold mb-2 block">I need...</label>
               <Select value={needType} onValueChange={setNeedType}>
                 <SelectTrigger className="w-full">
                   <SelectValue placeholder="Select necessity" />
                 </SelectTrigger>
                 <SelectContent>
                   <SelectItem value="labor">Labor / Workers</SelectItem>
                   <SelectItem value="equipment">Tractors / Equipment</SelectItem>
                   <SelectItem value="seeds">Seeds / Fertilizers</SelectItem>
                 </SelectContent>
               </Select>
            </div>
            <div className="flex-1 w-full">
               <label className="text-sm font-semibold mb-2 block">in location</label>
               <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="E.g. Punjab, Haryana" />
            </div>
            <Button onClick={handleSearch} className="bg-emerald-600 hover:bg-emerald-700 w-full md:w-auto h-10 px-8">
              <Search className="mr-2" size={18} /> Find
            </Button>
            <Button 
               onClick={handleVoiceSearch} 
               variant={voiceSearchActive ? "destructive" : "outline"} 
               className={voiceSearchActive ? "animate-pulse" : ""}
            >
              <Mic size={18} />
            </Button>
          </div>
        </GlassSection>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {matches.map((match, i) => (
            <Card key={i} className="hover:shadow-lg transition-shadow border-t-4 border-t-emerald-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex justify-between items-start">
                   {match.name}
                   {match.type === "labor" && <Users size={20} className="text-blue-500" />}
                   {match.type === "equipment" && <Tractor size={20} className="text-amber-500" />}
                   {match.type === "seeds" && <Wheat size={20} className="text-emerald-500" />}
                </CardTitle>
                <p className="text-sm text-gray-500">{match.location}</p>
              </CardHeader>
              <CardContent>
                <p className="font-bold text-xl text-emerald-700 mb-4">₹{match.rate}</p>
                <Button className="w-full bg-emerald-100 text-emerald-800 hover:bg-emerald-200">
                  Contact Match
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
