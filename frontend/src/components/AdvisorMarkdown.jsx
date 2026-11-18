import React from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// Presentation-only rounding; stored responses and grounding evidence stay intact.
export function readableCell(children) {
  return React.Children.map(children, child => {
    if (typeof child !== 'string') return child;
    return child.replace(/(^|\s)([+-]?\d+\.\d{3,})\s*%/g, (_,space,number) =>
      space + (number.startsWith('+') ? '+' : '') + Number(number).toFixed(2) + '%');
  });
}
const components = {
 a: ({href, children}) => href?.startsWith('/dashboard')
   ? <Link className="text-blue-700 underline" to={href}>{children}</Link>
   : <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-700 underline">{children}</a>,
 table: ({children}) => <div className="my-4 max-w-full overflow-x-auto rounded-lg border border-slate-300"><table className="w-full border-collapse text-left text-sm">{children}</table></div>,
 th: ({children}) => <th className="border-b border-slate-300 bg-blue-50 px-4 py-3 font-semibold whitespace-normal">{children}</th>,
 td: ({children}) => <td className="border-b border-slate-200 px-4 py-3 align-top whitespace-normal">{readableCell(children)}</td>,
};
export default function AdvisorMarkdown({children}) {
 return <div className="min-w-0 break-words whitespace-normal [&_p]:mb-3 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_strong]:font-semibold [&_pre]:overflow-x-auto [&_h3]:mb-2 [&_h3]:font-semibold"><ReactMarkdown remarkPlugins={[remarkGfm]} components={components} skipHtml>{children}</ReactMarkdown></div>;
}
