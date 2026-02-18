import React from 'react';

const Layout = ({ header, children }) => {
  return (
    <div className="min-h-screen bg-zinc-900 text-zinc-100 font-inter selection:bg-blue-500/30">
      {header}
      <main className="pt-24 px-4 pb-8 max-w-[1920px] mx-auto">
        {children}
      </main>
    </div>
  );
};

export default Layout;
