export default function AlertDetailBox({ title, content, styling = "" }) {
  return (
    <div className='details-box'>
      <p className='details-label'>{title}</p>
      <p className={`details-value ${styling}`}>{content}</p>
    </div>
  );
}
