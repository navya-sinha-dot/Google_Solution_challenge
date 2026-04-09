import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { LanguageProvider } from "@/contexts/LanguageContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { HardwareGate } from "@/components/HardwareGate";
import { VoiceAssistantButton } from "@/components/VoiceAssistantButton";
import { CallAgentButton } from "@/components/CallAgentButton";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import Trends from "./pages/Trends";
import Reports from "./pages/Reports";
import Advisor from "./pages/Advisor";
import SystemOverview from "./pages/SystemOverview";
import AIHardwareAccelerator from "./pages/AIHardwareAccelerator";
import MandiRates from "./pages/MandiRates";
import NotFound from "./pages/NotFound";
import Profile from "./pages/Profile";
import HardwareSetup from "./pages/HardwareSetup";
import BuyHardware from "./pages/BuyHardware";

import { ThemeProvider } from "next-themes";

const queryClient = new QueryClient();

// Redirect authenticated users away from login
// If authenticated but no hardware, send them to hardware setup first
function LoginRoute() {
  const { isAuthenticated, hardwareConnected } = useAuth();
  if (!isAuthenticated) return <Login />;
  return <Navigate to={hardwareConnected ? "/dashboard" : "/hardware-setup"} replace />;
}

const AppContent = () => {
  const { isAuthenticated } = useAuth();
  
  return (
    <>
      <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<LoginRoute />} />
                <Route path="/signup" element={<Signup />} />

                {/* Hardware onboarding — protected but no HardwareGate */}
                <Route
                  path="/hardware-setup"
                  element={
                    <ProtectedRoute>
                      <HardwareSetup />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/buy-hardware"
                  element={
                    <ProtectedRoute>
                      <BuyHardware />
                    </ProtectedRoute>
                  }
                />

                {/* Profile — protected, no HardwareGate (user needs to connect hardware here) */}
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <Profile />
                    </ProtectedRoute>
                  }
                />

                {/* Data pages — require hardware connection */}
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <HardwareGate>
                        <Dashboard />
                      </HardwareGate>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/trends"
                  element={
                    <ProtectedRoute>
                      <HardwareGate>
                        <Trends />
                      </HardwareGate>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/reports"
                  element={
                    <ProtectedRoute>
                      <HardwareGate>
                        <Reports />
                      </HardwareGate>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/advisor"
                  element={
                    <ProtectedRoute>
                      <HardwareGate>
                        <Advisor />
                      </HardwareGate>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/overview"
                  element={
                    <ProtectedRoute>
                      <HardwareGate>
                        <SystemOverview />
                      </HardwareGate>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/accelerator"
                  element={
                    <ProtectedRoute>
                      <HardwareGate>
                        <AIHardwareAccelerator />
                      </HardwareGate>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/mandi"
                  element={
                    <ProtectedRoute>
                      <HardwareGate>
                        <MandiRates />
                      </HardwareGate>
                    </ProtectedRoute>
                  }
                />

                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                <Route path="*" element={<NotFound />} />
              </Routes>
              {isAuthenticated && (
                <>
                  <VoiceAssistantButton />
                  <CallAgentButton />
                </>
              )}
    </>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <LanguageProvider>
        <AuthProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <BrowserRouter>
              <AppContent />
            </BrowserRouter>
          </TooltipProvider>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
