import { useState } from 'react';
import { Dashboard } from './pages/Dashboard';
import { APKs } from './pages/APKs';
import { Layout } from './components/Layout';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@flashdash/ui';
import { Zap, Package } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('flash');

  return (
    <Layout>
      <div className="container mx-auto p-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger value="flash" className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Flash
            </TabsTrigger>
            <TabsTrigger value="apks" className="flex items-center gap-2">
              <Package className="w-4 h-4" />
              APKs
            </TabsTrigger>
          </TabsList>
          <TabsContent value="flash">
            <Dashboard />
          </TabsContent>
          <TabsContent value="apks">
            <APKs />
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}

export default App;

