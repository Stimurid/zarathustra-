import { useState, useCallback, useRef, useEffect, type ReactNode } from 'react';

// Donor: quinta/src/components/RightDock.tsx @ 3963df4 — copied verbatim except
// for the DockTab union below, which is the only Workbench-specific seam.
export type DockMode = 'pinned' | 'overlay';
export type DockTab =
  // subject tabs — what the operator is looking at, not which subsystem owns it
  | 'overview' | 'io' | 'prompt' | 'rag' | 'settings' | 'contracts' | 'run';

interface RightDockProps {
  children: ReactNode;
  defaultWidth?: number;
  minWidth?: number;
  maxWidthPercent?: number;
  collapsed?: boolean;
  onCollapseChange?: (collapsed: boolean) => void;
  mode?: DockMode;
  onModeChange?: (mode: DockMode) => void;
  width?: number;
  onWidthChange?: (width: number) => void;
  activeTab?: DockTab;
  onTabChange?: (tab: DockTab) => void;
  tabs?: { id: DockTab; label: string; icon: string; content: ReactNode }[];
}

const COLLAPSED_WIDTH = 40;
const MIN_WIDTH_DEFAULT = 200;
const MAX_WIDTH_PERCENT_DEFAULT = 70;

export function RightDock({
  children,
  defaultWidth = 360,
  minWidth = MIN_WIDTH_DEFAULT,
  maxWidthPercent = MAX_WIDTH_PERCENT_DEFAULT,
  collapsed = false,
  onCollapseChange,
  mode = 'pinned',
  onModeChange,
  width: controlledWidth,
  onWidthChange,
  activeTab = 'inspector',
  onTabChange,
  tabs,
}: RightDockProps) {
  const [internalWidth, setInternalWidth] = useState(controlledWidth ?? defaultWidth);
  const [dragging, setDragging] = useState(false);
  const dockRef = useRef<HTMLDivElement>(null);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const currentWidth = controlledWidth ?? internalWidth;

  const setWidth = useCallback((w: number) => {
    const maxPx = (window.innerWidth * maxWidthPercent) / 100;
    const clamped = Math.max(minWidth, Math.min(w, maxPx));
    setInternalWidth(clamped);
    onWidthChange?.(clamped);
  }, [minWidth, maxWidthPercent, onWidthChange]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setDragging(true);
    dragStartX.current = e.clientX;
    dragStartWidth.current = currentWidth;
  }, [currentWidth]);

  useEffect(() => {
    if (!dragging) return;
    const handleMouseMove = (e: MouseEvent) => {
      const delta = dragStartX.current - e.clientX;
      setWidth(dragStartWidth.current + delta);
    };
    const handleMouseUp = () => setDragging(false);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragging, setWidth]);

  const toggleCollapse = useCallback(() => {
    onCollapseChange?.(!collapsed);
  }, [collapsed, onCollapseChange]);

  const toggleMode = useCallback(() => {
    onModeChange?.(mode === 'pinned' ? 'overlay' : 'pinned');
  }, [mode, onModeChange]);

  const dockStyle: React.CSSProperties = collapsed
    ? { width: COLLAPSED_WIDTH, minWidth: COLLAPSED_WIDTH }
    : { width: currentWidth, minWidth: minWidth };

  if (mode === 'overlay' && !collapsed) {
    dockStyle.position = 'absolute';
    dockStyle.right = 0;
    dockStyle.top = 0;
    dockStyle.bottom = 0;
    dockStyle.zIndex = 100;
  }

  return (
    <div
      ref={dockRef}
      className={`right-dock ${collapsed ? 'right-dock--collapsed' : ''} ${mode === 'overlay' ? 'right-dock--overlay' : ''} ${dragging ? 'right-dock--dragging' : ''}`}
      style={dockStyle}
    >
      {/* Resize handle */}
      {!collapsed && (
        <div
          className="right-dock__handle"
          onMouseDown={handleMouseDown}
        >
          <div className="right-dock__handle-bar" />
        </div>
      )}

      {/* Controls strip */}
      <div className="right-dock__controls">
        <button
          className="right-dock__ctrl-btn"
          onClick={toggleCollapse}
          title={collapsed ? 'Expand dock' : 'Collapse dock'}
        >
          {collapsed ? '◂' : '▸'}
        </button>
        {!collapsed && (
          <button
            className="right-dock__ctrl-btn"
            onClick={toggleMode}
            title={mode === 'pinned' ? 'Float (overlay)' : 'Pin to layout'}
          >
            {mode === 'pinned' ? '📌' : '🔲'}
          </button>
        )}
      </div>

      {/* Tab bar */}
      {!collapsed && tabs && (
        <div className="right-dock__tabs">
          {tabs.map(t => (
            <button
              key={t.id}
              className={`right-dock__tab ${activeTab === t.id ? 'right-dock__tab--active' : ''}`}
              onClick={() => onTabChange?.(t.id)}
              title={t.label}
            >
              <span className="right-dock__tab-icon">{t.icon}</span>
              <span className="right-dock__tab-label">{t.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Collapsed rail icons */}
      {collapsed && tabs && (
        <div className="right-dock__rail">
          {tabs.map(t => (
            <button
              key={t.id}
              className={`right-dock__rail-btn ${activeTab === t.id ? 'right-dock__rail-btn--active' : ''}`}
              onClick={() => {
                onTabChange?.(t.id);
                onCollapseChange?.(false);
              }}
              title={t.label}
            >
              {t.icon}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {!collapsed && (
        <div className="right-dock__content">
          {tabs
            ? tabs.find(t => t.id === activeTab)?.content ?? children
            : children
          }
        </div>
      )}
    </div>
  );
}
