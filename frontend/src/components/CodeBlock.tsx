import { Highlight, themes } from 'prism-react-renderer';

interface CodeBlockProps {
  code: string;
  language: string;
}

// Map common language aliases
const languageMap: Record<string, string> = {
  js: 'javascript',
  ts: 'typescript',
  tsx: 'tsx',
  jsx: 'jsx',
  py: 'python',
  sh: 'bash',
  shell: 'bash',
  zsh: 'bash',
  yml: 'yaml',
};

function normalizeLanguage(lang: string): string {
  const normalized = lang.toLowerCase().trim();
  return languageMap[normalized] || normalized;
}

export function CodeBlock({ code, language }: CodeBlockProps) {
  const normalizedLang = normalizeLanguage(language);

  return (
    <Highlight theme={themes.vsDark} code={code.trim()} language={normalizedLang}>
      {({ className, style, tokens, getLineProps, getTokenProps }) => (
        <pre
          className={`${className} rounded-md p-3 my-2 overflow-x-auto text-sm`}
          style={{ ...style, backgroundColor: '#1e1e1e' }}
        >
          {tokens.map((line, i) => (
            <div key={i} {...getLineProps({ line })}>
              <span className="text-zinc-600 select-none mr-4 text-xs inline-block w-6 text-right">
                {i + 1}
              </span>
              {line.map((token, key) => (
                <span key={key} {...getTokenProps({ token })} />
              ))}
            </div>
          ))}
        </pre>
      )}
    </Highlight>
  );
}

interface ParsedContent {
  type: 'text' | 'code';
  content: string;
  language?: string;
}

// Parse text content for markdown code blocks
export function parseCodeBlocks(text: string): ParsedContent[] {
  const parts: ParsedContent[] = [];
  // Match code blocks: ```language\ncode\n``` or ```\ncode\n```
  const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;

  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    // Add text before this code block
    if (match.index > lastIndex) {
      const textBefore = text.slice(lastIndex, match.index);
      if (textBefore.trim()) {
        parts.push({ type: 'text', content: textBefore });
      }
    }

    // Add the code block
    const language = match[1] || 'text';
    const code = match[2];
    parts.push({ type: 'code', content: code, language });

    lastIndex = match.index + match[0].length;
  }

  // Add any remaining text after the last code block
  if (lastIndex < text.length) {
    const remaining = text.slice(lastIndex);
    if (remaining.trim()) {
      parts.push({ type: 'text', content: remaining });
    }
  }

  // If no code blocks found, return the original text
  if (parts.length === 0) {
    parts.push({ type: 'text', content: text });
  }

  return parts;
}

interface HighlightedContentProps {
  content: string;
}

export function HighlightedContent({ content }: HighlightedContentProps) {
  const parts = parseCodeBlocks(content);

  return (
    <>
      {parts.map((part, index) =>
        part.type === 'code' ? (
          <CodeBlock key={index} code={part.content} language={part.language || 'text'} />
        ) : (
          <span key={index} className="whitespace-pre-wrap break-words">
            {part.content}
          </span>
        )
      )}
    </>
  );
}
