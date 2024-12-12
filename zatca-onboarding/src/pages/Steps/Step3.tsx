import { useAppDispatch, useAppSelector } from "@/app/hooks";
import DoneDialog from "@/components/DoneDialog";
import EditingForm from "@/components/EditingForm";
import { deleteData } from "@/data/dataSlice";
import { DataState } from "@/types";
import { useEffect, useRef, useState } from "react";
import Confetti from 'react-confetti';
import { FaPen, FaTrash } from "react-icons/fa";

const Step3 = () => {
  const dataState = useAppSelector((state) => state.dataReducer);
  const mainDiv = useRef<HTMLDivElement>(null);
  const [openIndex, setOpenIndex] = useState(null);
  const [checked, setChecked] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [showConfetti, setShowConfetti] = useState<boolean>(false);
  const [editingItem, setEditingItem] = useState<DataState | null>(null);
  const doneDialog = useRef<HTMLDialogElement>(null); 
  const editFormRef = useRef<HTMLDialogElement>(null);
  const dispatch = useAppDispatch();
  const handleEdit = (item: DataState) => {
    setEditingItem(item);
  };

  const handleDelete = (item: DataState) => {
    dispatch(deleteData(item))
  } 

  const handleSubmit = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setShowConfetti(true);
      doneDialog.current?.showModal()
    }, 1500)
  }
  const toggleDetails = (index: any) => {
    setOpenIndex(openIndex === index ? null : index); // Toggle the state
  };

  useEffect(() => {
    if (!editingItem) return;
    editFormRef.current?.showModal();
  }, [editingItem]);

  useEffect(() => {
    if (dataState.length === 0) window.location.reload()
  }, [dataState])


  return (
    <div ref={mainDiv} className="overflow-x-hidden w-full h-full flex flex-col justify-between p-5">
    {showConfetti ? <Confetti recycle={false} height={mainDiv.current?.offsetHeight} width={mainDiv.current?.offsetWidth} /> : null}
      <div>
      {dataState.map((item, index) => (
        <div key={index} className="group relative">
        <div
          className="bg-[#483f61] text-white p-4 rounded-md cursor-pointer transition-all duration-300 ease-in-out"
          onClick={() => toggleDetails(index)}
        >
          <summary className="text-xl font-semibold">
            <div className="flex justify-between w-full">
            {item.commercial_register_name}
            <div className={`${checked ? 'hidden' : ''} flex items-center gap-4`}>
              <div
                  onClick={() => handleEdit(item)}
                  className="tooltip tooltip-bottom cursor-pointer"
                  data-tip="Edit"
                >
                    <FaPen fontSize={15} />
              </div>
              <div
                  onClick={() => handleDelete(item)}
                  className="tooltip tooltip-bottom cursor-pointer"
                  data-tip="Delete"
                >
                <FaTrash color="red" fontSize={15} />
              </div>
            </div>
            </div>
          </summary>
        </div>

        <div
          className={`mt-4 bg-[#595c7a] text-white p-2 rounded-md transition-all duration-500 ease-in-out transform ${
            openIndex === index ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0'
          } overflow-hidden`}
        >
          <p><strong>Short Address:</strong> {item.short_address}</p>
          <p><strong>City:</strong> {item.city}</p>
          <p><strong>Building No:</strong> {item.building_no}</p>
          <p><strong>Address Line 1:</strong> {item.address_line1}</p>
          <p><strong>Address Line 2:</strong> {item.address_line2}</p>
          <p><strong>District:</strong> {item.district}</p>
          <p><strong>Postal Code:</strong> {item.pincode}</p>
          <p><strong>Commercial Register Number:</strong> {item.commercial_register_number}</p>
        </div>
      </div>
      ))}
      </div>
      <div className="p-5 self-end w-full flex justify-between items-center">
        <div className="form-control bg-transparent text-left">
          <label className="label cursor-pointer flex gap-4 p-0 justify-normal">
            <input
              type="checkbox"
              className="checkbox"
              onChange={() => setChecked(!checked)}
            />
            <span className="text-xl">
              I acknowledge that this data is correct and any mistakes are my
              responsibility
            </span>
          </label>
        </div>
        <button
        onClick={handleSubmit}
          disabled={!checked}
          className="btn bg-[#483f61] text-white border-none disabled:bg-gray-400"
          type="submit"
        >
          {loading ? <span className="loading loading-dots loading-lg"></span> : 'Submit'}
        </button>
      </div>
      {editingItem && (
        <EditingForm
          item={editingItem}
          ref={editFormRef}
          setEditingItem={setEditingItem}
        />
      )}
      <DoneDialog ref={doneDialog} />
    </div>

  );
};

export default Step3;
