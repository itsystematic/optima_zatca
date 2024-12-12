
interface ButtonProps {
  number: number;
  text: string;
  handleClick: (number : number) => void;
  img?: string;
  isActive?: number
}

const Button = (props: ButtonProps) => {
  const {handleClick, number, text, img, isActive} = props
  return (
    <button
      onClick={() => {
        handleClick(number);
      }}
      className={`${
        isActive === number
          ? "bg-[white] text-[#2a2439]"
          : "text-white bg-[#2a2439]"
      } w-[180px] transition-all duration-300 h-[180px] rounded-3xl flex flex-col items-center justify-center gap-3 hover:bg-white hover:text-[#2a2439] hover:scale-105 group`}
    >
      <div
        className={`${
          isActive === number
            ? "bg-[#2a2439] text-[#e8e8ef]"
            : "bg-[#d9d9d9] text-[#2a2439]"
        }  rounded-full w-16 h-16 flex transition-colors items-center justify-center text-4xl font-bold group-hover:bg-[#2a2439] group-hover:text-[#e8e8ef]`}
      >
        {img ? <img src={img} alt="None" /> : number}
      </div>
      <div className="text-2xl">{text}</div>
    </button>
  );
};

export default Button;
