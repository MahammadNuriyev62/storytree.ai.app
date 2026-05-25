import { Routes, Route, Link, useLocation } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Create from "./pages/Create.jsx";
import StoryDetails from "./pages/StoryDetails.jsx";
import Play from "./pages/Play.jsx";
import StoryTree from "./pages/StoryTree.jsx";

function Nav() {
  const { pathname } = useLocation();
  // The play screen is full-bleed/immersive — hide the chrome there.
  if (pathname.startsWith("/play/")) return null;
  return (
    <nav className="glass mx-3 mt-3 rounded-2xl px-4 py-3 flex items-center justify-between sticky top-3 z-20">
      <Link to="/" className="text-xl font-bold tracking-tight hover:scale-105 transition">
        📚 StoryTree 🌳
      </Link>
      <div className="flex gap-5 text-sm">
        <Link to="/" className="hover:text-purple-200 transition">Stories</Link>
        <Link to="/create" className="hover:text-purple-200 transition">✨ Create</Link>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <div className="min-h-screen">
      <Nav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/create" element={<Create />} />
        <Route path="/story/:id" element={<StoryDetails />} />
        <Route path="/story/:id/tree" element={<StoryTree />} />
        <Route path="/play/:id" element={<Play />} />
      </Routes>
    </div>
  );
}
