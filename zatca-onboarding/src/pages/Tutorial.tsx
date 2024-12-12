import Carousel from "@/components/Carousel";
import Form from "@/components/Form";
import { forwardRef } from "react";

interface TutorialProps {
  handleTutorialClick: () => void
}


const Tutorial = forwardRef<HTMLDialogElement, TutorialProps>(
  (props, ref) => {
    return (
      <Form ref={ref}>
        <TutorialChildren handleTutorialClick={props.handleTutorialClick} />
      </Form>
    );
  }
);


const TutorialChildren = ({ handleTutorialClick }: { handleTutorialClick: () => void }) => {
  return (
    <>
      <form method="dialog">
        <button className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">
          ✕
        </button>
      </form>
      <h3 className="font-medium text-lg text-center">How it works!</h3>
      <div className="h-[500px]">
        <Carousel />
      </div>
      <div className="modal-action bg-transparent m-0  flex-grow w-full">
        <form
          method="dialog"
          className="w-full flex flex-col justify-center items-center gap-5"
        >
          <button
            onClick={handleTutorialClick}
            className="btn bg-[#483f61] rounded-md w-[40%] text-white mt-2"
          >
            Let's Get Started!!
          </button>
          <div className="text-white">
            Continuing Means That You Agree To Our Terms Aand Conditions
          </div>
        </form>
      </div>
    </>
  );
};


export default Tutorial;
