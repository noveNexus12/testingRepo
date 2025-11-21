import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Download } from 'lucide-react';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL).replace(/\/$/, '');

export default function DataExport() {
  const [dataset, setDataset] = useState('telemetry');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      let url = `${API_BASE_URL}/export/${dataset}`;
      if (start && end && dataset !== 'report') {
        url += `?start=${start}&end=${end}`;
      }
      window.open(url, '_blank');
    } catch (err) {
      console.error('Download failed:', err);
      alert('Something went wrong while downloading the file.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <Card className="border-border shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-gray-800">Data Export</CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {/* Dataset Selector */}
            <div>
              <label className="block text-sm text-muted-foreground mb-2">Dataset</label>
              <Select onValueChange={setDataset} defaultValue={dataset}>
                <SelectTrigger>
                  <SelectValue placeholder="Select dataset" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="telemetry">Telemetry</SelectItem>
                  <SelectItem value="alerts">Alerts</SelectItem>
                  <SelectItem value="poles">Poles</SelectItem>
                  <SelectItem value="report">Pole Health Report</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Start Date */}
            <div>
              <label className="block text-sm text-muted-foreground mb-2">Start Date</label>
              <Input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                disabled={dataset === 'report'}
                className={dataset === 'report' ? 'opacity-50 cursor-not-allowed' : ''}
              />
            </div>

            {/* End Date */}
            <div>
              <label className="block text-sm text-muted-foreground mb-2">End Date</label>
              <Input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                disabled={dataset === 'report'}
                className={dataset === 'report' ? 'opacity-50 cursor-not-allowed' : ''}
              />
            </div>
          </div>

          <Button
            onClick={handleDownload}
            disabled={loading || ((start || end) && !(start && end))}
            className="mt-4 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            {loading ? 'Preparing...' : 'Download CSV'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
