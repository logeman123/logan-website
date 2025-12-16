'use client';

import { useEffect } from 'react';

export default function ResumeLayout({
  children,
}: {
  children: React.ReactNode
}) {
  useEffect(() => {
    // Add jungle theme class to body when on resume page
    document.body.classList.add('jungle-theme');

    // Remove it when leaving the page
    return () => {
      document.body.classList.remove('jungle-theme');
    };
  }, []);

  return <>{children}</>;
}
