import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { setData } from "@/data/dataSlice";
import { Card, Flex, Image, Typography } from "antd";

const Phases = () => {
  const dispatch = useAppDispatch();
  const dataState = useAppSelector((state) => state.dataReducer);

  type Phases = {
    [k in "img" | "id" | "name"]: string;
  };

  const phases: Phases[] = [
    {
      img: !isDev
        ? "/assets/optima_zatca/zatca-onboarding/Phase_1.svg"
        : "Phase_1.svg",
      id: "Phase One",
      name: "Phase 1",
    },
    {
      img: !isDev
        ? "/assets/optima_zatca/zatca-onboarding/Phase_2.svg"
        : "Phase_2.svg",
      id: "Phase Two",
      name: "Phase 2",
    },
  ];

  const handlePhaseSelect = (phase: string) => {
    dispatch(setData({ ...dataState, phase }));
    dispatch(setCurrentPage(3));
  };

  return (
    <Flex align="center" vertical className="h-full">
      <Flex className="h-1/3" align="center">
        <Typography.Title className="text-[#483f61]">{__("Company Phase?")}</Typography.Title>
      </Flex>
      <Flex gap={16} justify="center" align="center" className="mt-6">
        {phases.map((phase) => (
          <Card
            onClick={() => handlePhaseSelect(phase.id)}
            key={phase.id}
            hoverable
            className="transition-all group bg-[#2a2439] text-white duration-300 w-[180px] h-[180px] flex justify-center items-center rounded-3xl hover:bg-white cursor-pointer hover:text-white border-none"
          >
            <div className="flex justify-center items-center flex-col gap-5">
              <Image
                preview={false}
                width={120}
                src={phase.img}
                alt="Expressive Image"
                className=" transition-all duration-300"
              />

              <Typography.Text className="text-xl font-medium text-white group-hover:text-black">
                {__(phase.name)}
              </Typography.Text>
            </div>
          </Card>
        ))}
      </Flex>
    </Flex>
  );
};

export default Phases;
