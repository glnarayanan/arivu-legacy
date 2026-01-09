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
      <DialogContent aria-describedby="shortcuts-description">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl uppercase tracking-wide">Keyboard Shortcuts</DialogTitle>
          <p id="shortcuts-description" className="text-sm text-muted-foreground sr-only">
            View all available keyboard shortcuts
          </p>
        </DialogHeader>
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {shortcuts.map((shortcut, idx) => (
            <div key={idx} className="flex items-center justify-between py-2 border-b-2 border-foreground last:border-0">
              <span className="font-mono text-sm text-muted-foreground uppercase tracking-wider">{shortcut.description}</span>
              <kbd className="px-3 py-1.5 font-mono text-xs bg-muted border-2 border-foreground shadow-brutal-sm">
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </div>
        <div className="mt-4 p-4 bg-muted border-2 border-foreground">
          <p className="font-mono text-xs text-muted-foreground text-center uppercase tracking-wider">
            Press <kbd className="px-2 py-0.5 font-mono text-xs bg-background border-2 border-foreground">?</kbd> anytime to view shortcuts
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default KeyboardShortcutsModal;
