import Button from '@/components/Button';
import Form from '@/components/Form';
import { forwardRef, useState } from 'react';
import { IoIosArrowBack } from 'react-icons/io';

interface PhasesProps {
    handlePhasesBack: () => void;
    handlePhaseSubmit: () => void
}

const Phases = forwardRef<HTMLDialogElement, PhasesProps>((props, ref) => {
    
  return (
    <Form ref={ref}>
        <PhasesChildren handlePhasesBack={props.handlePhasesBack} handlePhaseSubmit={props.handlePhaseSubmit} />
    </Form>
  )
})

export default Phases


const PhasesChildren = ({
    handlePhasesBack,
    handlePhaseSubmit
  }: {
    handlePhasesBack: () => void;
    handlePhaseSubmit: () => void
  }) => {

  const [isActive, setIsActive] = useState<number>();
    
    return (
      <>
        <form method="dialog">
          <button
            onClick={handlePhasesBack}
            className="btn btn-sm btn-circle btn-ghost absolute left-2 top-2 text-lg"
          >
            <IoIosArrowBack />
          </button>
        </form>
        <div className="flex h-full gap-16">
          <div className="h-full w-full flex items-center justify-end">
            <Button isActive={isActive} handleClick={() => {
              setIsActive(1)
              handlePhaseSubmit()
            }} number={1} text={"المرحلة الاولة"} />
          </div>
          <div className="h-full w-full flex items-center">
            <Button isActive={isActive} handleClick={() => {
              setIsActive(2)
              handlePhaseSubmit()
            }} number={2} text={"المرحلة الثانية"} />
          </div>
        </div>
      </>
    );
  };
  