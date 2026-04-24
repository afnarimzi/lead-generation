import { BrowserRouter, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import Search from './pages/Search';
import MyJobs from './pages/MyJobs';
import Leads from './pages/Leads';
import LeadDetail from './pages/LeadDetail';

function Navigation() {
  const location = useLocation();
  
  const isActive = (path: string) => {
    return location.pathname === path ? 'bg-blue-700' : 'hover:bg-blue-700';
  };

  return (
    <nav className="flex gap-2">
      <Link
        to="/search"
        className={`px-4 py-2 rounded transition ${isActive('/search')}`}
      >
        🔍 Search
      </Link>
      <Link
        to="/my-jobs"
        className={`px-4 py-2 rounded transition ${isActive('/my-jobs')}`}
      >
        ⭐ My Jobs
      </Link>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <header className="bg-blue-600 text-white shadow-lg">
          <div className="container mx-auto px-4 py-4">
            <div className="flex justify-between items-center">
              <h1 className="text-2xl font-bold">🤖 Freelance Lead Scraper</h1>
              <Navigation />
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/search" replace />} />
            <Route path="/search" element={<Search />} />
            <Route path="/leads" element={<Leads />} />
            <Route path="/leads/:id" element={<LeadDetail />} />
            <Route path="/my-jobs" element={<MyJobs />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-200 mt-12">
          <div className="container mx-auto px-4 py-6 text-center text-gray-600">
            <p>Freelance Lead Scraper v1.0.0</p>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}
