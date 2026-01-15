import { useState } from 'react';
import axiosInstance from '../../utils/axiosConfig';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { toast } from 'sonner';
import { Download, Loader2, FileText, FileJson, FileSpreadsheet } from 'lucide-react';

const BackupSection = () => {
  const [loading, setLoading] = useState(false);
  const [format, setFormat] = useState('html');
  const [includeNotes, setIncludeNotes] = useState(true);
  const [includeAiSummaries, setIncludeAiSummaries] = useState(true);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const handleBackup = async () => {
    setLoading(true);

    try {
      const requestData = {
        format,
        include_notes: includeNotes,
        include_ai_summaries: includeAiSummaries,
      };

      if (dateFrom) {
        requestData.date_from = new Date(dateFrom).toISOString();
      }
      if (dateTo) {
        requestData.date_to = new Date(dateTo).toISOString();
      }

      const response = await axiosInstance.post('/bookmarks/backup', requestData, {
        responseType: 'blob'
      });

      // Get filename from Content-Disposition header
      const contentDisposition = response.headers['content-disposition'];
      let filename = `arivu_backup.${format}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/);
        if (match) {
          filename = match[1];
        }
      }

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success('Backup downloaded successfully');
    } catch (error) {
      toast.error('Failed to create backup');
    } finally {
      setLoading(false);
    }
  };

  const formats = [
    { id: 'html', label: 'HTML', icon: FileText, description: 'Browser-compatible bookmark file' },
    { id: 'json', label: 'JSON', icon: FileJson, description: 'Full data with AI summaries & notes' },
    { id: 'csv', label: 'CSV', icon: FileSpreadsheet, description: 'Spreadsheet-friendly format' },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="font-display text-2xl uppercase tracking-wide mb-2">Backup & Export</h2>
        <p className="font-mono text-xs text-muted-foreground uppercase tracking-wider">
          Download your bookmarks in various formats
        </p>
      </div>

      {/* Format Selection */}
      <div className="space-y-4">
        <Label className="font-mono text-xs uppercase tracking-wider">Export Format</Label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {formats.map((f) => {
            const Icon = f.icon;
            const isSelected = format === f.id;
            return (
              <button
                key={f.id}
                onClick={() => setFormat(f.id)}
                className={`
                  p-4 border-2 text-left transition-all
                  ${isSelected
                    ? 'border-foreground bg-foreground text-background'
                    : 'border-foreground hover:bg-muted'
                  }
                `}
              >
                <Icon className={`w-6 h-6 mb-2 ${isSelected ? 'text-background' : ''}`} />
                <h4 className="font-heading font-bold uppercase">{f.label}</h4>
                <p className={`font-mono text-xs ${isSelected ? 'text-background/70' : 'text-muted-foreground'}`}>
                  {f.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Options */}
      <div className="space-y-4">
        <Label className="font-mono text-xs uppercase tracking-wider">Include in Backup</Label>
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeAiSummaries}
              onChange={(e) => setIncludeAiSummaries(e.target.checked)}
              className="w-5 h-5 border-2 border-foreground rounded-none accent-primary"
            />
            <span className="font-mono text-sm">AI Summaries & Tags</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeNotes}
              onChange={(e) => setIncludeNotes(e.target.checked)}
              className="w-5 h-5 border-2 border-foreground rounded-none accent-primary"
            />
            <span className="font-mono text-sm">Personal Notes</span>
          </label>
        </div>
      </div>

      {/* Date Range */}
      <div className="space-y-4">
        <Label className="font-mono text-xs uppercase tracking-wider">Date Range (Optional)</Label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="dateFrom" className="font-mono text-xs text-muted-foreground">From</Label>
            <Input
              id="dateFrom"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-none border-2 border-foreground font-mono"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="dateTo" className="font-mono text-xs text-muted-foreground">To</Label>
            <Input
              id="dateTo"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-none border-2 border-foreground font-mono"
            />
          </div>
        </div>
        <p className="font-mono text-xs text-muted-foreground">
          Leave empty to export all bookmarks
        </p>
      </div>

      {/* Download Button */}
      <div className="pt-4 border-t-2 border-foreground">
        <Button
          onClick={handleBackup}
          disabled={loading}
          className="rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              GENERATING BACKUP...
            </>
          ) : (
            <>
              <Download className="w-4 h-4 mr-2" />
              DOWNLOAD BACKUP
            </>
          )}
        </Button>
      </div>

      {/* Info Box */}
      <div className="p-4 bg-muted border-2 border-foreground">
        <p className="font-mono text-xs uppercase tracking-wider mb-2 font-medium">
          Backup Information
        </p>
        <ul className="font-mono text-xs text-muted-foreground space-y-1">
          <li>• <strong>HTML:</strong> Import into any browser (Chrome, Firefox, Safari)</li>
          <li>• <strong>JSON:</strong> Best for complete data backup with all metadata</li>
          <li>• <strong>CSV:</strong> Open in Excel, Google Sheets, or other spreadsheet apps</li>
        </ul>
      </div>
    </div>
  );
};

export default BackupSection;
