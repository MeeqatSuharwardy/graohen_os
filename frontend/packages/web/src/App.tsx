import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Landing } from './pages/Landing';
import { Demo } from './pages/Demo';
import { Dashboard } from './pages/Dashboard';
import { Downloads } from './pages/Downloads';
import { Layout } from './components/Layout';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/demo" element={<Demo />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/downloads" element={<Downloads />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;

