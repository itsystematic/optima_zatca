import { forwardRef } from "react"

const DoneDialog = forwardRef<HTMLDialogElement>((_, ref) => {
  return (
    <dialog ref={ref} id="success" className="modal">
  <div className="modal-box">
    <h3 className="font-bold text-lg">Congratulations!!!</h3>
    <p className="py-4">Success</p>
  </div>
  <form method="dialog" className="modal-backdrop">
    <button>close</button>
  </form>
</dialog>
  )
})

export default DoneDialog