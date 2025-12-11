import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';

const shortcuts = [
  { key: 'Q', description: 'Quick Add Bookmark' },
  { key: '/ or F', description: 'Search' },
  { key: 'Esc', description: 'Dismiss/Cancel' },
  { key: '?', description: 'Show keyboard shortcuts' },
  { key: 'Cmd/Ctrl + K', description: 'Open Quick Find' },
  { key: 'Cmd/Ctrl + P', description: 'Print current view' },
  { key: '↑ ↓', description: 'Navigate bookmarks' },
  { key: 'Enter', description: 'Open selected bookmark' },
];

const KeyboardShortcutsModal = ({ open, onOpenChange }) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-2xl" aria-describedby="shortcuts-description">
        <DialogHeader>
          <DialogTitle className="font-heading text-2xl">Keyboard Shortcuts</DialogTitle>
          <p id="shortcuts-description" className="text-sm text-muted-foreground sr-only">
            View all available keyboard shortcuts
          </p>
        </DialogHeader>
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {shortcuts.map((shortcut, idx) => (
            <div key={idx} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
              <span className="text-sm text-muted-foreground">{shortcut.description}</span>
              <kbd className="px-3 py-1.5 text-xs font-mono bg-muted border border-border rounded-lg">
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </div>
        <div className="mt-4 p-4 bg-muted/50 rounded-xl">
          <p className="text-xs text-muted-foreground text-center">
            Press <kbd className="px-2 py-0.5 text-xs font-mono bg-background border border-border rounded">?</kbd> anytime to view shortcuts
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default KeyboardShortcutsModal;
