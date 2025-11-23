import { useState, useEffect } from 'react';
import bgImage from './assets/installer_bg.png';

function App() {
  const [version] = useState<string>('0.1.0');

  useEffect(() => {
    // In a real app, we might fetch this from package.json or Electron IPC
    // For now, hardcoded is fine for the demo
  }, []);

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center text-white bg-cover bg-center bg-no-repeat font-sans"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      {/* Overlay for better text readability if needed */}
      <div className="absolute inset-0 bg-black/50 z-0"></div>

      <div className="relative z-10 text-center p-8 rounded-lg border border-white/10 bg-black/60 backdrop-blur-sm max-w-md w-full shadow-2xl">
        <h1 className="text-5xl font-extrabold mb-2 tracking-wider text-red-600 drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">
          MAXIMUM SECURITY
        </h1>

        <div className="w-full h-px bg-gradient-to-r from-transparent via-red-600 to-transparent my-6 opacity-50"></div>

        <p className="text-gray-300 text-lg mb-8">
          LAUNCHER V{version}
        </p>

        <div className="space-y-4">
          <p className="text-sm text-emerald-400 font-mono">
            ✓ SYSTEM ONLINE
          </p>
          <p className="text-sm text-emerald-400 font-mono">
            ✓ CONNECTION ESTABLISHED
          </p>
          <p className="text-sm text-emerald-400 font-mono animate-pulse">
            ✓ WAITING FOR INPUT...
          </p>
        </div>

        <div className="mt-10 pt-6 border-t border-white/10 text-xs text-gray-500 font-mono">
          SECURE CONNECTION // ENCRYPTED
        </div>
      </div>
    </div>
  )
}

export default App
