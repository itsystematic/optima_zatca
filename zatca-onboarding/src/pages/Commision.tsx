import { useAppDispatch } from '@/app/hooks'
import Button from '@/components/Button'
import Form from '@/components/Form'
import { setCommission } from '@/data/commission'
import { forwardRef, useState } from 'react'
import { IoIosArrowBack } from 'react-icons/io'

interface CommisionProps {
    handleCommisionBack : () => void    
    handleCommissionSubmit: () => void
}

const Commision = forwardRef<HTMLDialogElement, CommisionProps>((props, ref) => {
  return (
    <Form ref={ref}>
        <CommissionChildren handleCommissionSubmit={props.handleCommissionSubmit} handleCommisionBack={props.handleCommisionBack} />
    </Form>
  )
})


const CommissionChildren = ({handleCommisionBack, handleCommissionSubmit} : CommisionProps) => {
  const [isActive, setIsActive] = useState<number>();
  const dispatch = useAppDispatch();
  return (
<>
      <form method="dialog">
      <button
            onClick={handleCommisionBack}
            className="btn btn-sm btn-circle btn-ghost absolute left-2 top-2 text-lg"
          >
            <IoIosArrowBack />
          </button>
      </form>
      <h3 className="font-bold text-4xl text-center">هل الشركة تملك؟؟</h3>
      <div className='flex flex-col gap-5 justify-center items-center h-full'>
        <div className='flex gap-5'>
            <Button isActive={isActive} handleClick={() => {handleCommissionSubmit(); setIsActive(3); dispatch(setCommission({commission: 'main'}))}} img={isDev ? `MainCommision.png` : `/assets/optima_zatca/zatca-onboarding/MainCommision.png`} number={3} text={"سجل التجاري رئيسي"} />
            <Button isActive={isActive} handleClick={() => {handleCommissionSubmit(); setIsActive(4); dispatch(setCommission({commission: 'multi'}))}} img={isDev ? 'MultipleCommision.png' : `/assets/optima_zatca/zatca-onboarding/MultipleCommision.png`} number={4} text={"سجلات تجارية فرعية"} />
        </div>
      </div>
      

    </>
  )
}

export default Commision