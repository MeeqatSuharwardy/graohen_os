import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@flashdash/ui';
import { Zap, Package } from 'lucide-react';
import { FlasherPage } from './pages/FlasherPage';
import { APKsPage } from './pages/APKsPage';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('flash');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            FlashDash
          </h1>
          <p className="text-gray-600">
            Flash GrapheneOS to Pixel devices via browser WebUSB
          </p>
        </header>

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
            <FlasherPage />
          </TabsContent>

          <TabsContent value="apks">
            <APKsPage />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default App;

