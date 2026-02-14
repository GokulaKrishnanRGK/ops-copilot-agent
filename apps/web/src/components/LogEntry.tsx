type LogEntryProps = {
  text: string;
};

export function LogEntry({ text }: LogEntryProps) {
  return <pre className="message-log">{text}</pre>;
}
