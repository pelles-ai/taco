import CommandPalette from '@site/src/components/CommandPalette';

/**
 * Docusaurus theme Root override. Wraps the entire app — used here to mount
 * the global CMD+K command palette so the keyboard shortcut works on every
 * page without per-page integration.
 */
export default function Root({children}) {
  return (
    <>
      {children}
      <CommandPalette />
    </>
  );
}
