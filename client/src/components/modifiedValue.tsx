export const ModifiedValue = ({
  current,
  base,
}: {
  current: number;
  base: number;
}) => {
  if (current == base) {
    return <span className={"neutral-modified"}>{current}</span>;
  }
  if (current > base) {
    return (
      <>
        <span className={"increased-modified"}>{current}</span>
        <span>{`(${base})`}</span>
      </>
    );
  }
  return (
    <>
      <span className={"decreased-modified"}>{current}</span>
      <span>{`(${base})`}</span>
    </>
  );
};
