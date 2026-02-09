import { Chrome } from 'lucide-react';
import { StaggerContainer, StaggerItem } from '../motion/PageOrchestrator';

const XLogo = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

const ConnectionsSection = () => {
  return (
    <StaggerContainer className="space-y-6">
      {/* X (Twitter) — Extension-Based Capture */}
      <StaggerItem>
        <div className="border-2 border-foreground bg-card p-6 shadow-brutal-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-foreground text-background">
              <XLogo className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-heading font-bold uppercase tracking-wide">X (Twitter)</h4>
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Save tweets via browser extension
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="p-4 border-2 border-foreground bg-muted">
              <div className="flex items-start gap-3">
                <Chrome className="w-5 h-5 mt-0.5 flex-shrink-0 text-primary" />
                <div className="space-y-2">
                  <p className="text-sm">
                    Save tweets directly using the <strong>Arivu browser extension</strong>.
                    While viewing any tweet on x.com:
                  </p>
                  <ul className="text-sm text-muted-foreground space-y-1 ml-1">
                    <li className="flex items-center gap-2">
                      <span className="font-mono text-xs bg-foreground text-background px-1.5 py-0.5">1</span>
                      Click the Arivu extension icon in your toolbar
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="font-mono text-xs bg-foreground text-background px-1.5 py-0.5">2</span>
                      Or right-click and select "Save tweet to Arivu"
                    </li>
                  </ul>
                  <p className="text-sm text-muted-foreground">
                    Tweet text, author, and metrics are captured automatically and processed through the AI pipeline.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </StaggerItem>
    </StaggerContainer>
  );
};

export default ConnectionsSection;
