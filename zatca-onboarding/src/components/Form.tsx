import React, { forwardRef, useEffect } from "react";

const Form = forwardRef<HTMLDialogElement, React.PropsWithChildren>(
  ({ children }, ref) => {

        
    useEffect(() => {
      const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === "Escape") {
          event.preventDefault();
        }
      };

      const dialogElement = ref as React.RefObject<HTMLDialogElement>;

      if (dialogElement?.current) {
        dialogElement.current.addEventListener("keydown", handleKeyDown);
      }

      return () => {
        if (dialogElement?.current) {
          dialogElement.current.removeEventListener("keydown", handleKeyDown);
        }
      };
    }, [ref]);


    return (
      <dialog
        ref={ref}
        className="modal bg-cover bg-center"
        style={{
          backgroundImage: `url(${
            isDev
              ? "Tutorial.png"
              : "/assets/optima_zatca/zatca-onboarding/Tutorial.png"
          })`,
        }}
      >
        <div className="modal-box max-h-[80vh] pb-0 max-w-[65vw] px-0 bg-[#483f6140] flex flex-col h-screen rounded-sm">
          {children}
        </div>
      </dialog>
    );
  }
);

export default Form;
